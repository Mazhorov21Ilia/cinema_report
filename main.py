from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from hashlib import sha256
from db import Database
from kivy.lang import Builder
from kivy.core.window import Window                      
from kivy.graphics import Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from io import BytesIO
import matplotlib.pyplot as plt
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image as KivyImage
from kivy.uix.checkbox import CheckBox


def show_popup(title, message):
        popup = Popup(
            title=title,
            content=Label(text=message, ),
            size_hint=(0.8, 0.4),
            title_align='center',
            background_color=(0, 0, 0, 1)
        )
        popup.open()



class LoginScreen(Screen):
    Window.size = (400, 600)
    def on_pre_enter(self, *args):
        self.ids.username.text = ''
        self.ids.password.text = ''

    def login(self):
        username = self.ids.username.text.strip()
        password = self.ids.password.text.strip()

        if not username or not password:
            show_popup("Ошибка", "Введите имя пользователя и пароль!")
            return

        

        hashed_password = sha256(password.encode()).hexdigest()

        query = "SELECT * FROM users WHERE username = %s AND password_hash = %s"
        user = self.manager.db.fetch_one(query, (username, hashed_password))

        if user:
            self.manager.current_user = user
            self.manager.current = 'home'
            self.manager.db.log_action(App.get_running_app().root.current_user['id'], 'Вход пользователя')

        else:
            show_popup("Ошибка", "Неверное имя пользователя или пароль!")

    def registration(self):
        username = self.ids.username.text
        password = self.ids.password.text

        if not username or not password:
            show_popup("Ошибка", "Введите имя пользователя и пароль!")
            return
        
        if len(password) < 5:
            show_popup("Ошибка", "Пароль должен быть минимум 5 символов")
            return

        hashed_password = sha256(password.encode()).hexdigest()

        existing_user = self.manager.db.fetch_one("SELECT * FROM users WHERE username = %s", (username,))

        if existing_user:
            show_popup("Внимание!", "Такой пользователь уже есть.")
            return

        self.manager.db.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'user')",
                                (username, hashed_password))

        # self.manager.db.log_action(App.get_running_app().root.current_user['id'], 'Регистрация')

        show_popup("Внимание!", "Пользователь зарегистрирован!")
        self.login()


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_pre_enter(self):
        current_user = App.get_running_app().root.current_user
        if current_user:
            self.ids.username_label.text = f"Добро пожаловать, {current_user['username']}!"


class FilmsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_pre_enter(self):
        current_user = App.get_running_app().root.current_user
        if current_user:
            self.ids.username_label.text = f"Фильмы {current_user['username']}"


class FilmsWatchedScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_categories = []
        self.categories = ["Комедия", "Драма", "Детектив", "Анимация", "Спорт"]

    def on_enter(self):
        self.update_films_list()

    def open_add_film_popup(self):
        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        film_input = TextInput(hint_text='Название фильма', multiline=False, size_hint_y=None, height=40)

        # Категории
        categories_layout = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        categories_layout.bind(minimum_height=categories_layout.setter('height'))
        category_checkboxes = {}
        
        for category in self.categories:
            category_box = BoxLayout(size_hint_y=None, height=40)
            checkbox = CheckBox(size_hint_x=0.2)
            label = Label(text=category, size_hint_x=0.8)
            category_box.add_widget(checkbox)
            category_box.add_widget(label)
            categories_layout.add_widget(category_box)
            category_checkboxes[category] = checkbox

        categories_scroll = ScrollView(size_hint=(1, 0.4))
        categories_scroll.add_widget(categories_layout)

        confirm_button = Button(text='Добавить фильм', size_hint_y=None, height=50, on_release=lambda btn: self.add_film(film_input.text.strip(), category_checkboxes, popup))
        cancel_button = Button(text='Отмена', size_hint_y=None, height=50, on_release=lambda btn: popup.dismiss())

        popup_layout.add_widget(film_input)
        popup_layout.add_widget(Label(text="Выберите категории:", size_hint_y=None, height=30))
        popup_layout.add_widget(categories_scroll)
        popup_layout.add_widget(confirm_button)
        popup_layout.add_widget(cancel_button)

        popup = Popup(title="Добавить фильм", content=popup_layout, size_hint=(0.8, 0.8))
        popup.open()

    def add_film(self, film_name, category_checkboxes, popup):
        if not film_name:
            show_popup("Ошибка", "Введите название фильма!")
            return

        selected_categories = [category for category, checkbox in category_checkboxes.items() if checkbox.active]
        if not selected_categories:
            show_popup("Ошибка", "Выберите хотя бы одну категорию!")
            return

        user_id = App.get_running_app().root.current_user['id']
        self.manager.db.log_action(self.manager.db.cursor.lastrowid, 'Добавление фильма в просмотренные')

        query_film = "INSERT INTO films (user_id, film_name) VALUES (%s, %s)"
        self.manager.db.execute(query_film, (user_id, film_name))

        film_id = self.manager.db.cursor.lastrowid
        query_category = "INSERT INTO film_categories (film_id, category) VALUES (%s, %s)"
        for category in selected_categories:
            self.manager.db.execute(query_category, (film_id, category))
        show_popup("Успех", "Фильм успешно добавлен!")
        popup.dismiss()
        self.update_films_list()
        
    def update_films_list(self):
        self.ids.films_list.clear_widgets()
        try:
            user_id = App.get_running_app().root.current_user['id']

            query = """
                SELECT films.id, films.film_name, GROUP_CONCAT(film_categories.category SEPARATOR ', ') AS categories
                FROM films
                LEFT JOIN film_categories ON films.id = film_categories.film_id
                WHERE films.user_id = %s
                GROUP BY films.id
            """
            films = self.manager.db.fetch_all(query, (user_id,))

            for film in films:
                film_layout = BoxLayout(size_hint_y=None, height=40)
                film_label = Label(
                    text=f"{film['film_name']} ({film['categories']})",
                    size_hint_x=0.8
                )
                delete_button = Button(
                    text="Удалить",
                    size_hint_x=0.35, 
                    background_color=(0.286, 0.149, 0.42, 1),
                    on_release=lambda btn, film_id=film['id']: self.delete_film(film_id)
                )
                film_layout.add_widget(film_label)
                film_layout.add_widget(delete_button)
                self.ids.films_list.add_widget(film_layout)
        except:
            pass

    def delete_film(self, film_id):
        try:
            delete_categories_query = "DELETE FROM film_categories WHERE film_id = %s"
            self.manager.db.execute(delete_categories_query, (film_id,))

            delete_film_query = "DELETE FROM films WHERE id = %s"
            self.manager.db.execute(delete_film_query, (film_id,))

            show_popup("Успех", "Фильм успешно удален!")
            self.update_films_list()
        except Exception as e:
            show_popup("Ошибка", f"Не удалось удалить фильм: {str(e)}")

    def show_statistics(self):
        """Отображает статистику категорий."""
        user_id = App.get_running_app().root.current_user['id']
        query = """
            SELECT category, COUNT(category) as count
            FROM film_categories
            INNER JOIN films ON films.id = film_categories.film_id
            WHERE films.user_id = %s
            GROUP BY category
        """
        stats = self.manager.db.fetch_all(query, (user_id,))

        categories = [stat['category'] for stat in stats]
        counts = [stat['count'] for stat in stats]

        if not categories:
            show_popup("Информация", "Нет данных для статистики!")
            return

        plt.figure(figsize=(6, 8))
        plt.bar(categories, counts, color='skyblue')
        plt.title("Статистика любимых категорий")
        plt.xlabel("Категории")
        plt.ylabel("Количество")
        plt.yticks(range(1, max(counts) + 1))

        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        img = CoreImage(buf, ext='png')
        graph_popup = Popup(
            title="Статистика",
            content=KivyImage(texture=img.texture),
            size_hint=(0.9, 0.9)
        )
        graph_popup.open()


class UserPasswordScreen(Screen):
    def save_new_password(self):
        user_id = App.get_running_app().root.current_user['id']
        password = self.ids.new_password.text.strip()
        password_confirm = self.ids.confirm_password.text.strip()

        password_hash = None

        if password or password_confirm:
            if password != password_confirm:
                show_popup("Ошибка", "Пароли не совпадают!")
                return
            
            if len(password) < 5:
                show_popup("Ошибка", "Пароль должен быть минимум 5 символов")
                return
            password_hash = Database.hash_password(password)
            query = """
                            UPDATE users
                            SET password_hash = %s 
                            WHERE id = %s
                        """
            self.manager.db.execute(query, (password_hash, user_id))

            show_popup("Внимание!", "Пароль изменен!")

            self.manager.db.log_action(user_id, 'Изменение пароля')
            self.manager.current = 'login'
        else:
            show_popup("Ошибка", "Введите пароль")
        

class PlannedFilmsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_categories = []
        self.categories = ["Комедия", "Драма", "Детектив", "Анимация", "Спорт"]

    def on_enter(self, *args):
        self.update_films_list()

    def open_add_film_popup(self):
        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        film_input = TextInput(hint_text='Название фильма', multiline=False, size_hint_y=None, height=40)

        categories_layout = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        categories_layout.bind(minimum_height=categories_layout.setter('height'))
        category_checkboxes = {}
        
        for category in self.categories:
            category_box = BoxLayout(size_hint_y=None, height=40)
            checkbox = CheckBox(size_hint_x=0.2)
            label = Label(text=category, size_hint_x=0.8)
            category_box.add_widget(checkbox)
            category_box.add_widget(label)
            categories_layout.add_widget(category_box)
            category_checkboxes[category] = checkbox

        categories_scroll = ScrollView(size_hint=(1, 0.4))
        categories_scroll.add_widget(categories_layout)

        confirm_button = Button(text='Добавить фильм', size_hint_y=None, height=50, on_release=lambda btn: self.add_film(film_input.text.strip(), category_checkboxes, popup))
        cancel_button = Button(text='Отмена', size_hint_y=None, height=50, on_release=lambda btn: popup.dismiss())

        popup_layout.add_widget(film_input)
        popup_layout.add_widget(Label(text="Выберите категории:", size_hint_y=None, height=30))
        popup_layout.add_widget(categories_scroll)
        popup_layout.add_widget(confirm_button)
        popup_layout.add_widget(cancel_button)

        popup = Popup(title="Добавить фильм", content=popup_layout, size_hint=(0.8, 0.8))
        popup.open()
    
    def add_film(self, film_name, category_checkboxes, popup):
        if not film_name:
            show_popup("Ошибка", "Введите название фильма!")
            return

        selected_categories = [category for category, checkbox in category_checkboxes.items() if checkbox.active]
        if not selected_categories:
            show_popup("Ошибка", "Выберите хотя бы одну категорию!")
            return

        user_id = App.get_running_app().root.current_user['id']
        self.manager.db.log_action(self.manager.db.cursor.lastrowid, 'Добавление фильма в отложенные')

        query_film = "INSERT INTO planned_films (user_id, film_name) VALUES (%s, %s)"
        self.manager.db.execute(query_film, (user_id, film_name))

        film_id = self.manager.db.cursor.lastrowid
        query_category = "INSERT INTO planned_film_categories (film_id, category) VALUES (%s, %s)"
        for category in selected_categories:
            self.manager.db.execute(query_category, (film_id, category))
        show_popup("Успех", "Фильм успешно добавлен!")
        popup.dismiss()
        self.update_films_list()

    def update_films_list(self):
        films_layout = self.ids.planned_films_list
        films_layout.clear_widgets()

        try:
            user_id = App.get_running_app().root.current_user['id']
            query = """
                SELECT planned_films.id, planned_films.film_name,
                       GROUP_CONCAT(planned_film_categories.category SEPARATOR ', ') AS categories
                FROM planned_films
                LEFT JOIN planned_film_categories ON planned_films.id = planned_film_categories.film_id
                WHERE planned_films.user_id = %s
                GROUP BY planned_films.id
            """
            films = self.manager.db.fetch_all(query, (user_id,))

            for film in films:
                film_id = film['id']
                film_name = film['film_name']
                categories = film['categories']

                film_item = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
                film_label = Label(text=f"{film_name} ({categories})", size_hint_x=0.8)
                watched_button = Button(text="Просмотрено", size_hint_x=0.35, background_color=(0.286, 0.149, 0.42, 1))
                watched_button.bind(on_release=lambda instance, fid=film_id, fname=film_name: self.mark_as_watched(fid, fname))

                film_item.add_widget(film_label)
                film_item.add_widget(watched_button)
                films_layout.add_widget(film_item)
        except Exception as e:
            print(f"Ошибка обновления списка запланированных фильмов: {e}")

    def add_planned_film(self, film_name):
        user_id = App.get_running_app().root.current_user['id']

        if not film_name:
            show_popup("Ошибка", "Введите название фильма!")
            return

        query = "INSERT INTO planned_films (user_id, film_name) VALUES (%s, %s)"
        try:
            self.manager.db.execute(query, (user_id, film_name))
            show_popup("Успех", "Фильм добавлен в запланированные!")
            self.update_films_list()
        except Exception as e:
            show_popup("Ошибка", f"Не удалось добавить фильм: {e}")

    def remove_planned_film(self, film_id):
        """Удаляет фильм из запланированных."""
        self.manager.db.execute("DELETE FROM planned_film_categories WHERE film_id = %s", (film_id,))
        self.manager.db.execute("DELETE FROM planned_films WHERE id = %s", (film_id,))

    def mark_as_watched(self, film_id, film_name):
        """Переносит фильм из запланированных в просмотренные."""
        user_id = App.get_running_app().root.current_user['id']

        query_watched = "INSERT INTO films (user_id, film_name) VALUES (%s, %s)"
        self.manager.db.execute(query_watched, (user_id, film_name))
        watched_film_id = self.manager.db.cursor.lastrowid

        # Переносим категории фильма
        query_categories = """
            SELECT category FROM planned_film_categories WHERE film_id = %s
        """
        categories = self.manager.db.fetch_all(query_categories, (film_id,))
        query_add_category = "INSERT INTO film_categories (film_id, category) VALUES (%s, %s)"
        for category in categories:
            self.manager.db.execute(query_add_category, (watched_film_id, category['category']))

        # Удаляем фильм из запланированных
        self.remove_planned_film(film_id)
        show_popup("Успех", f"'{film_name}' перенесен в просмотренные!")
        self.update_films_list()


class NotesApp(ScreenManager):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Database()
        self.current_user = None
        Window.size = (400, 600)
        self.add_widget(LoginScreen(name='login'))
        self.add_widget(HomeScreen(name='home'))
        self.add_widget(FilmsScreen(name='films'))
        self.add_widget(UserPasswordScreen(name='user_password'))
        self.add_widget(FilmsWatchedScreen(name='films_watched'))
        self.add_widget(PlannedFilmsScreen(name='planned_films'))
        self.set_background()

    def set_background(self):
        with self.canvas.before:
            self.rect = Rectangle(source='cinema.jpg', pos=self.pos, size=(400, 600))

    
class CinemaReportApp(App):
    def build(self):
        Builder.load_file(r'kivy_files\login.kv')
        Builder.load_file(r'kivy_files\home.kv')
        Builder.load_file(r'kivy_files\change_user_password.kv')
        Builder.load_file(r'kivy_files\films.kv')
        Builder.load_file(r'kivy_files\films_watched.kv')
        Builder.load_file(r'kivy_files\planned_films.kv')
        return NotesApp()


if __name__ == '__main__':
    CinemaReportApp().run()
