import datetime
from collections import deque
import random
import csv
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import PhotoImage
from typing import Optional
from sys import platform

from PIL import Image
from CTkMessagebox import CTkMessagebox
import customtkinter as ctk
import fitz
import pyttsx3

from colors import (YELLOW_BACKGROUND, PINK_BACKGROUND,
                    GREEN_BACKGROUND, SWAMP_FOREGROUND,
                    ORANGE_FOREGROUND, NEW_USER_WINDOW_FOREGROUND,
                    PINK_FOREGROUND, CRIMSON_HOVER,
                    BEGIN_BUTTON_FOREGROUND_COLOR, BEGIN_BUTTON_HOVER_COLOR,
                    SOUNDS_BUTTONS_FOREGROUND, SOUNDS_BUTTONS_HOVER,
                    POSITIVE_BUTTON_FOREGROUND, POSITIVE_BUTTON_HOVER,
                    NEGATIVE_BUTTON_FOREGROUND, NEGATIVE_BUTTON_HOVER,
                    ANSWER_BUTTON_FOREGROUND, ANSWER_BUTTON_HOVER,
                    CHECKBOX_HOVER_COLOR, PROGRESS_FOREGROUND,
                    PROGRESS_COLOR, GREEN,
                    RED, WHITE, ERROR_COLOR, PDF_OUTPUT_COLOR)
from settings import (CREATE_USER_WINDOW, HINT_WINDOW_TITLE,
                      Theme, QuestionThreshold as qt,
                      ValidResponse,
                      APP_NAME, APP_RESOLUTION)
from models import create_db
from manage_db import (create_new_user, get_user_names,
                       get_user_interview_duration,
                       get_user_progress, get_last_enter_date,
                       update_interview_duration, update_last_enter_date,
                       update_user_progress, delete_this_user)
from user_statistics import (convert_seconds_to_hours,
                             count_interview_duration,
                             get_right_answers_amount,
                             get_last_enter_message)
from validator import (is_name_empty, is_name_too_short,
                       has_name_first_wrong_symbol, has_name_wrong_symbols,
                       is_name_too_long, is_user_already_exists)
from my_timers import CommandTimer, MessageTimer


class Main(ctk.CTk):
    """Main class for the App governing vars between other classes."""
    def __init__(self, title: str, size: tuple[int, int]) -> None:
        super().__init__()
        # Setup
        self.title(title)
        self.geometry(f'{size[0]}x{size[1]}')
        self.resizable(False, False)
        self.iconbitmap(default='images/icon.ico')

        # Instance vars
        self.current_user: str = ''
        self.volume: float = 0.5
        self.user_progress: dict = {}
        self.create_user_window: Optional[CreateNewUser] = None
        self.hint_window: Optional[HintWindow] = None

        # Load questions and create question bank
        self.question_bank = self.load_csv()

        # Themes dictionary
        self.themes: dict[int, Theme] = {
            0: Theme.BASICS,
            1: Theme.OOP,
            2: Theme.PEP8,
            3: Theme.STRUCTURES,
            4: Theme.ALGHORITMS,
            5: Theme.GIT,
            6: Theme.SQL
        }

        # Interview mode dictionary
        self.interview_mode: dict[Theme | str, int] = {
            Theme.BASICS: 1,
            Theme.OOP: 0,
            Theme.PEP8: 0,
            Theme.STRUCTURES: 0,
            Theme.ALGHORITMS: 0,
            Theme.GIT: 0,
            Theme.SQL: 0,
            'Freemode': 0,
            'Random': 0
        }

        # Notebook
        self.notebook = ctk.CTkTabview(
            self,
            segmented_button_fg_color='black',
            segmented_button_selected_color='green',
            segmented_button_selected_hover_color='green',
            text_color='white',
            segmented_button_unselected_color='black',
            segmented_button_unselected_hover_color='black')
        self.notebook.pack(
            padx=20,
            pady=20,
            side='left',
            fill='both',
            expand=True
            )

        self.notebook.add(name='Профиль пользователей')
        self.notebook.add(name='Настройки собеседования')
        self.notebook.add(name='Пройти собеседование')
        self.notebook.set('Профиль пользователей')

        # Tabs of notebook
        self.userstats = UserStatisticsTab(
            parent=self.notebook.tab('Профиль пользователей'),
            create_new_user=self.create_new_user,
            set_current_user=self.set_current_user,
            set_user_progress=self.set_user_progress,
            set_color_for_user_progress=self.set_color_for_user_progress
            )

        self.interview_settings = InterviewSettingsTab(
            parent=self.notebook.tab('Настройки собеседования'),
            set_interview_mode=self.set_interview_mode,
            get_volume=self.get_volume,
            set_volume=self.set_volume
            )

        self.interview_pass = InterviewPassTab(
            parent=self.notebook.tab('Пройти собеседование'),
            themes=self.themes,
            database=self.question_bank,
            show_hint_window=self.show_hint_window,
            get_volume=self.get_volume,
            set_volume=self.set_volume,
            get_current_user=self.get_current_user,
            set_notebook_status=self.set_notebook_status,
            get_interview_mode=self.get_interview_mode,
            get_user_progress=self.get_user_progress,
            update_progress=self.update_progress,
            )

    def load_csv(self) -> list[tuple[int | str]]:
        """Converts data.csv to list of tuples."""
        with open('data.csv', encoding='utf-8', mode='r') as f:
            reader = csv.reader(f, delimiter=';')
            data = tuple(reader)
        return [
            tuple(
                [int(item) if item.isdigit() else item for item in row]
                ) for row in data]

    def create_new_user(self) -> None:
        """Makes a new window to create a new user."""
        if self.create_user_window is None or not self.create_user_window.winfo_exists():
            self.create_user_window = CreateNewUser(
                title=CREATE_USER_WINDOW,
                update_combobox=self.update_combobox
                )
            self.focus()
            self.create_user_window.focus()
        else:
            self.create_user_window.lift()
            self.create_user_window.focus()

    def show_hint_window(self, filepath: str, page_number: int) -> None:
        """Makes a new window to show the answer to the question."""
        if self.hint_window is None or not self.hint_window.winfo_exists():
            self.hint_window = HintWindow(
                HINT_WINDOW_TITLE,
                filepath,
                page_number
                )
            self.focus()
            self.hint_window.focus()
        else:
            self.hint_window.lift()
            self.hint_window.focus()

    def get_volume(self) -> float:
        """Returns current a volume value."""
        return self.volume

    def set_volume(self, volume: float) -> None:
        """Sets transferred value of volume."""
        self.volume = volume
        if not self.volume:
            self.interview_pass.mute_button.configure(
                image=self.interview_pass.mute_button_img_OFF
                )
        else:
            self.interview_pass.mute_button.configure(
                image=self.interview_pass.mute_button_img_ON
                )
        hundred_volume = 100 * self.volume
        self.interview_settings.sound_volume.set(hundred_volume)
        self.interview_settings.sound_text.set(
            f'Громкость: {int(hundred_volume)}%'
            )

    def update_combobox(self) -> None:
        """Updates user list at the user statistics tab."""
        self.userstats.update_user_list()

    def update_progress(self) -> None:
        """Updates users progress bars at the user statistics tab."""
        self.userstats.update_user_progress()

    def set_interview_mode(self,
                           interview_mode: dict[Theme | str, int]) -> None:
        """Sets parametres of interview according selection
        at user settings tab.
        """
        self.interview_mode = interview_mode

    def set_current_user(self, current_user: str) -> None:
        """Sets a name of user from another tabs."""
        self.current_user = current_user

    def get_current_user(self) -> str:
        """Returns current user name."""
        return self.current_user

    def set_notebook_status(self, status: str) -> None:
        """Sets notebook state according transferred value."""
        self.notebook.configure(state=status)

    def get_interview_mode(self) -> dict[Theme | str, int]:
        """Returns the interview mode uncluding:
        - chosen themes
        - is chosen a Random mode
        - is chosen a Free mode.
        """
        return self.interview_mode

    def set_user_progress(self, user_progress: dict) -> None:
        """Sets user progress according value."""
        self.user_progress = user_progress

    def get_user_progress(self) -> None:
        """Returns current user progress."""
        return self.user_progress

    def set_color_for_user_progress(self) -> None:
        """Updates question strings' color
        at the user intervew tab,
        according current user progress.
        """
        self.interview_pass.set_color_for_user_progress()


class UserStatisticsTab(ctk.CTkFrame):
    """Class for showing user statistics tab."""
    def __init__(self, parent, create_new_user,
                 set_current_user, set_user_progress,
                 set_color_for_user_progress):
        # Setup
        super().__init__(parent)
        self.width = 1000
        self.place(x=0, y=0)
        self.columnconfigure((0, 1), weight=1)
        self.rowconfigure((0, 1), weight=1)

        # Users vars
        self.create_new_user = create_new_user
        self.users = get_user_names()
        self.current_user = set_current_user
        self.set_user_progress = set_user_progress
        self.chosen_user = None
        self.set_color_for_user_progress = set_color_for_user_progress

        # MESSAGE VARS
        # pink screen
        self.user_var = tk.StringVar(value='Выберите пользователя...')

        # yellow screen
        self.last_enter_message = tk.StringVar()
        self.interview_duration_message = tk.StringVar()
        self.rigth_answer_message = tk.StringVar()
        self.percentage_completion_message = tk.StringVar()

        self.create_widgets()
        self.author_note()
        self.set_to_zero_progress_bars()

        # EVENTS
        self.combobox1.bind("<<ComboboxSelected>>", self.choose_user)

    def update_user_list(self) -> None:
        """Updates the list of users in Combobox."""
        self.combobox1['values'] = get_user_names()

    def reset_settings(self) -> None:
        """Turns to zero any in statistics."""
        self.chosen_user = None
        self.current_user(self.chosen_user)
        self.user_var.set('Выберите пользователя...')
        self.last_enter_message.set('')
        self.interview_duration_message.set('')
        self.rigth_answer_message.set('')
        self.percentage_completion_message.set('')

    def update_user_progress(self) -> None:
        """Updates everything in current user statistics."""
        progress = get_right_answers_amount(
            get_user_progress(self.chosen_user)
            )
        self.last_enter_message.set(
            get_last_enter_message(
                get_last_enter_date(self.chosen_user)
                )
                )
        self.interview_duration_message.set(
            f'{convert_seconds_to_hours(
                get_user_interview_duration(self.chosen_user))} ч.'
            )
        self.rigth_answer_message.set(progress['right_answers_amount'])
        self.percentage_completion_message.set(
            progress['percentage_completion']
            )
        self.basic_progress_bar.set(progress['basic_progress'])
        self.oop_progress_bar.set(progress['oop_progress'])
        self.pep_progress_bar.set(progress['pep_progress'])
        self.structures_progress_bar.set(progress['structures_progress'])
        self.alghoritms_progress_bar.set(progress['alghorimts_progress'])
        self.git_progress_bar.set(progress['git_progress'])
        self.sql_progress_bar.set(progress['sql_progress'])

    def set_to_zero_progress_bars(self) -> None:
        """Turns to zero every progress bar."""
        self.basic_progress_bar.set(0)
        self.oop_progress_bar.set(0)
        self.pep_progress_bar.set(0)
        self.structures_progress_bar.set(0)
        self.alghoritms_progress_bar.set(0)
        self.git_progress_bar.set(0)
        self.sql_progress_bar.set(0)

    def delete_user(self) -> None:
        """Deletes the chosen user from DB and screen."""
        delete_this_user(self.chosen_user)
        self.reset_settings()
        self.update_user_list()
        self.set_to_zero_progress_bars()

    def choose_user(self, event) -> None:
        """Processes event choosing a user.
        It updates everything at the tab.
        """
        self.chosen_user = self.user_var.get()
        self.current_user(self.chosen_user)
        self.set_user_progress(get_user_progress(self.chosen_user))
        self.get_current_user_statistics()
        self.update_user_progress()
        self.set_color_for_user_progress()

    def get_current_user_statistics(self) -> None:
        """Gets current user statistics."""
        self.last_enter_message.set(
            get_last_enter_message(get_last_enter_date(self.chosen_user))
        )

        self.interview_duration_message.set(
            f'{convert_seconds_to_hours(
                get_user_interview_duration(self.chosen_user))} ч.'
            )

        messages_data = get_right_answers_amount(
            get_user_progress(self.chosen_user)
            )
        self.rigth_answer_message.set(messages_data['right_answers_amount'])
        self.percentage_completion_message.set(
            messages_data['percentage_completion']
            )

    def author_note(self) -> None:
        """Shows a title of author."""
        self.author_label = ctk.CTkLabel(
            master=self,
            text='github.com/IvanZaycev0717\n\nTelegram: @ivanzaycev0717'
        )
        self.author_label.place(x=20, y=560)

    def create_widgets(self) -> None:
        """Creates widgets at the user statistics tab."""
        # PINK SCREEN
        self.choose_user_frame = ctk.CTkFrame(
            self,
            fg_color=PINK_BACKGROUND,
            width=600,
            height=300
            )
        self.choose_user_frame.grid(
            row=0,
            column=0,
            sticky='n',
            padx=20,
            pady=20
            )

        # Static labels
        self.user_manage_label = ctk.CTkLabel(
            self.choose_user_frame,
            text='Управление пользователями',
            font=('Calibri', 25)
            )
        self.user_manage_label.place(x=30, y=10)
        self.choose_user_label = ctk.CTkLabel(
            self.choose_user_frame,
            text='Выберите пользователя',
            font=('Calibri', 18))
        self.choose_user_label.place(x=30, y=50)
        self.create_new_user_label = ctk.CTkLabel(
            self.choose_user_frame,
            text='Вы можете создать нового пользователя',
            font=('Calibri', 18)
            )
        self.create_new_user_label.place(x=30, y=200)

        # Combobox
        self.combobox1 = ttk.Combobox(
            self.choose_user_frame,
            textvariable=self.user_var,
            state="readonly")
        self.combobox1.configure(values=self.users)
        self.combobox1.place(x=30, y=80, width=250, height=35)

        # Images at the buttons
        self.create_user_button_img = ctk.CTkImage(
            light_image=Image.open('images/add.png').resize((30, 30)),
            dark_image=Image.open('images/add.png').resize((30, 30))
        )
        self.delete_user_button_img = ctk.CTkImage(
            light_image=Image.open('images/delete.png').resize((30, 30)),
            dark_image=Image.open('images/delete.png').resize((30, 30))
        )

        # Buttons
        self.create_user_button = ctk.CTkButton(
            self.choose_user_frame,
            width=250,
            height=35,
            fg_color=PINK_FOREGROUND,
            hover_color=CRIMSON_HOVER,
            text='Создать пользователя',
            image=self.create_user_button_img,
            text_color='black',
            command=self.create_new_user)
        self.create_user_button.place(x=30, y=240)

        self.delete_user_button = ctk.CTkButton(
            self.choose_user_frame,
            width=200,
            height=35,
            fg_color=PINK_FOREGROUND,
            hover_color=CRIMSON_HOVER,
            text='Удалить пользователя',
            image=self.delete_user_button_img,
            text_color='black',
            command=self.delete_user)
        self.delete_user_button.place(x=320, y=80)

        # YELLOW SCREEN
        # frame
        self.global_stats_frame = ctk.CTkFrame(
            self,
            fg_color=YELLOW_BACKGROUND,
            width=400,
            height=250
            )
        self.global_stats_frame.grid(
            row=1,
            column=0,
            sticky='e',
            padx=20,
            pady=20
            )

        # Static labels
        self.global_stat_label = ctk.CTkLabel(
            self.global_stats_frame,
            text='Глобальная статистика',
            font=('Calibri', 25)
            )
        self.global_stat_label.place(x=30, y=10)
        self.last_enter_label = ctk.CTkLabel(
            self.global_stats_frame,
            text='Собеседование было:',
            font=('Calibri', 18)
            )
        self.last_enter_label.place(x=30, y=60)
        self.interview_duration_label = ctk.CTkLabel(
            self.global_stats_frame,
            text='Время собеседований:',
            font=('Calibri', 18)
            )
        self.interview_duration_label.place(x=30, y=110)
        self.right_answer_amount_label = ctk.CTkLabel(
            self.global_stats_frame,
            text='Правильных ответов:',
            font=('Calibri', 18)
            )
        self.right_answer_amount_label.place(x=30, y=160)
        self.percentage_completion_label = ctk.CTkLabel(
            self.global_stats_frame,
            text='Процент завершения:',
            font=('Calibri', 18)
            )
        self.percentage_completion_label.place(x=30, y=210)

        # Dynamic messages of user's staticstics
        self.last_enter_message_label = ttk.Label(
            master=self.global_stats_frame,
            textvariable=self.last_enter_message,
            font=('Calibri', 16),
            background=YELLOW_BACKGROUND
            )
        self.last_enter_message_label.place(x=215, y=58)

        self.interview_duration_message_label = tk.Label(
            master=self.global_stats_frame,
            textvariable=self.interview_duration_message,
            font=('Calibri', 16),
            background=YELLOW_BACKGROUND
        )
        self.interview_duration_message_label.place(x=220, y=107)

        self.rigth_answer_message_label = ttk.Label(
            master=self.global_stats_frame,
            textvariable=self.rigth_answer_message,
            font=('Calibri', 16),
            background=YELLOW_BACKGROUND
        )
        self.rigth_answer_message_label.place(x=205, y=157)

        self.percentage_completion_message_label = ttk.Label(
            master=self.global_stats_frame,
            textvariable=self.percentage_completion_message,
            font=('Calibri', 16),
            background=YELLOW_BACKGROUND
        )
        self.percentage_completion_message_label.place(x=205, y=208)

        # GREEN SCREEN
        # Frame
        self.particular_stats_frame = ctk.CTkFrame(
            self,
            fg_color=GREEN_BACKGROUND,
            width=550
            )
        self.particular_stats_frame.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky='nsew',
            padx=20,
            pady=20
            )

        self.detail_progress_title = ctk.CTkLabel(
            self.particular_stats_frame,
            text='Детальный прогресс по собеседованиям',
            font=('Calibri', 25)
            )
        self.detail_progress_title.place(x=30, y=10)

        # Basic syntax progress
        self.basic_progress_label = ctk.CTkLabel(
            self.particular_stats_frame,
            text=Theme.BASICS.value,
            font=('Calibri', 18)
            )
        self.basic_progress_label.place(x=30, y=60)

        self.basic_progress_bar = ctk.CTkProgressBar(
            self.particular_stats_frame,
            width=480,
            height=30,
            fg_color=PROGRESS_FOREGROUND,
            progress_color=PROGRESS_COLOR)
        self.basic_progress_bar.place(x=30, y=90)

        # OOP progress
        self.oop_progress_label = ctk.CTkLabel(
            self.particular_stats_frame,
            text=Theme.OOP.value,
            font=('Calibri', 18)
            )
        self.oop_progress_label.place(x=30, y=130)

        self.oop_progress_bar = ctk.CTkProgressBar(
            self.particular_stats_frame,
            width=480,
            height=30,
            fg_color=PROGRESS_FOREGROUND,
            progress_color=PROGRESS_COLOR)
        self.oop_progress_bar.place(x=30, y=160)

        # PEP progress
        self.pep_progress_label = ctk.CTkLabel(
            self.particular_stats_frame,
            text='Правила оформления кода (PEP8, PEP257)',
            font=('Calibri', 18)
            )
        self.pep_progress_label.place(x=30, y=200)

        self.pep_progress_bar = ctk.CTkProgressBar(
            self.particular_stats_frame,
            width=480,
            height=30,
            fg_color=PROGRESS_FOREGROUND,
            progress_color=PROGRESS_COLOR)
        self.pep_progress_bar.place(x=30, y=230)

        # Structures progress
        self.structures_progress_label = ctk.CTkLabel(
            self.particular_stats_frame,
            text=Theme.STRUCTURES.value,
            font=('Calibri', 18)
            )
        self.structures_progress_label.place(x=30, y=270)

        self.structures_progress_bar = ctk.CTkProgressBar(
            self.particular_stats_frame,
            width=480,
            height=30,
            fg_color=PROGRESS_FOREGROUND,
            progress_color=PROGRESS_COLOR)
        self.structures_progress_bar.place(x=30, y=300)

        # Alghoritms progress
        self.alghoritms_progress_label = ctk.CTkLabel(
            self.particular_stats_frame,
            text=Theme.ALGHORITMS.value,
            font=('Calibri', 18)
            )
        self.alghoritms_progress_label.place(x=30, y=340)

        self.alghoritms_progress_bar = ctk.CTkProgressBar(
            self.particular_stats_frame,
            width=480,
            height=30,
            fg_color=PROGRESS_FOREGROUND,
            progress_color=PROGRESS_COLOR)
        self.alghoritms_progress_bar.place(x=30, y=370)

        # GIT progress
        self.git_progress_label = ctk.CTkLabel(
            self.particular_stats_frame,
            text=Theme.GIT.value,
            font=('Calibri', 18)
            )
        self.git_progress_label.place(x=30, y=410)

        self.git_progress_bar = ctk.CTkProgressBar(
            self.particular_stats_frame,
            width=480,
            height=30,
            fg_color=PROGRESS_FOREGROUND,
            progress_color=PROGRESS_COLOR)
        self.git_progress_bar.place(x=30, y=440)

        # SQL progress
        self.sql_progress_label = ctk.CTkLabel(
            self.particular_stats_frame,
            text=Theme.SQL.value,
            font=('Calibri', 18)
            )
        self.sql_progress_label.place(x=30, y=480)

        self.sql_progress_bar = ctk.CTkProgressBar(
            self.particular_stats_frame,
            width=480,
            height=30,
            fg_color=PROGRESS_FOREGROUND,
            progress_color=PROGRESS_COLOR)
        self.sql_progress_bar.place(x=30, y=510)


class InterviewSettingsTab(ctk.CTkFrame):
    """Class for choosing interview's settings."""
    def __init__(self, parent, set_interview_mode, get_volume, set_volume):
        super().__init__(parent)
        self.width = 1200
        self.place(x=0, y=0)
        self.columnconfigure((0, ), weight=1)
        self.rowconfigure((0, 1, 2, 3), weight=1)
        self.set_interview_mode = set_interview_mode

        # Flags in Checkboxes
        self.basics_chosen = ctk.IntVar(value=1)
        self.oop_chosen = ctk.IntVar(value=0)
        self.pep_chosen = ctk.IntVar(value=0)
        self.structures_chosen = ctk.IntVar(value=0)
        self.alghoritms_chosen = ctk.IntVar(value=0)
        self.git_chosen = ctk.IntVar(value=0)
        self.sql_chosen = ctk.IntVar(value=0)

        # Flags in sequence mode
        self.are_random_questions = ctk.IntVar(value=0)

        # Flag in free mode
        self.freemode_var = ctk.IntVar()
        self.get_volume = get_volume
        self.set_volume = set_volume
        self.sound_volume = ctk.IntVar(value=int(100 * self.get_volume()))
        self.sound_text = ctk.StringVar(
            value=f'Громкость: {self.sound_volume.get()}%'
            )

        self.choose_interview_mode_tab()
        self.choose_random_interview()
        self.choose_free_mode()
        self.toggle_sounds()

    def draw_line(self, frame) -> None:
        """Draws a line near a setting title."""
        self.tab_line = ctk.CTkCanvas(
            frame,
            width=5,
            height=80,
            bd=0,
            highlightthickness=0
            )
        self.tab_line.place(x=400, y=10)
        self.tab_line.create_line(0, 0, 0, 80, width=10)

    def draw_label(self, frame, text) -> None:
        """Draws a label of setting with custom text."""
        ctk.CTkLabel(frame, text=text, font=('Calibri', 20)).place(x=20, y=35)

    def choose_interview_mode_tab(self) -> None:
        """Creates a choice of themes for interview."""
        self.choose_interview_mode_frame = ctk.CTkFrame(
            self, fg_color=SWAMP_FOREGROUND,
            width=1185,
            height=100
            )
        self.choose_interview_mode_frame.grid(
            row=0,
            column=0,
            sticky='n',
            padx=20,
            pady=20
            )
        self.draw_label(
            self.choose_interview_mode_frame,
            'Выбор тем собеседования'
            )
        self.draw_line(self.choose_interview_mode_frame)

        self.basics = ctk.CTkCheckBox(
            master=self.choose_interview_mode_frame,
            text=Theme.BASICS.value,
            hover_color=CHECKBOX_HOVER_COLOR,
            fg_color=CHECKBOX_HOVER_COLOR,
            variable=self.basics_chosen,
            command=self.add_chosen_theme)
        self.basics.place(x=420, y=15)

        self.oop = ctk.CTkCheckBox(
            master=self.choose_interview_mode_frame,
            text='ООП Python',
            hover_color=CHECKBOX_HOVER_COLOR,
            fg_color=CHECKBOX_HOVER_COLOR,
            variable=self.oop_chosen,
            command=self.add_chosen_theme)
        self.oop.place(x=420, y=55)

        self.pep = ctk.CTkCheckBox(
            master=self.choose_interview_mode_frame,
            text='PEP8, PEP257',
            hover_color=CHECKBOX_HOVER_COLOR,
            fg_color=CHECKBOX_HOVER_COLOR,
            variable=self.pep_chosen,
            command=self.add_chosen_theme)
        self.pep.place(x=650, y=15)

        self.structures = ctk.CTkCheckBox(
            master=self.choose_interview_mode_frame,
            text=Theme.STRUCTURES.value,
            hover_color=CHECKBOX_HOVER_COLOR,
            fg_color=CHECKBOX_HOVER_COLOR,
            variable=self.structures_chosen,
            command=self.add_chosen_theme)
        self.structures.place(x=650, y=55)

        self.alghoritms = ctk.CTkCheckBox(
            master=self.choose_interview_mode_frame,
            text=Theme.ALGHORITMS.value,
            hover_color=CHECKBOX_HOVER_COLOR,
            fg_color=CHECKBOX_HOVER_COLOR,
            variable=self.alghoritms_chosen,
            command=self.add_chosen_theme)
        self.alghoritms.place(x=870, y=15)

        self.sql = ctk.CTkCheckBox(
            master=self.choose_interview_mode_frame,
            text=Theme.SQL.value,
            hover_color=CHECKBOX_HOVER_COLOR,
            fg_color=CHECKBOX_HOVER_COLOR,
            variable=self.sql_chosen,
            command=self.add_chosen_theme)
        self.sql.place(x=870, y=55)

        self.git = ctk.CTkCheckBox(
            master=self.choose_interview_mode_frame,
            text=Theme.GIT.value,
            hover_color=CHECKBOX_HOVER_COLOR,
            fg_color=CHECKBOX_HOVER_COLOR,
            variable=self.git_chosen,
            command=self.add_chosen_theme)
        self.git.place(x=1100, y=15)

    def add_chosen_theme(self) -> None:
        """Transfers chosen settings to the main class."""
        # Freemode special behavior
        if self.freemode_var.get():
            self.basics_chosen.set(1)
            self.oop_chosen.set(1)
            self.pep_chosen.set(1)
            self.structures_chosen.set(1)
            self.alghoritms_chosen.set(1)
            self.git_chosen.set(1)
            self.sql_chosen.set(1)
            self.basics.configure(state=tk.DISABLED)
            self.oop.configure(state=tk.DISABLED)
            self.pep.configure(state=tk.DISABLED)
            self.structures.configure(state=tk.DISABLED)
            self.alghoritms.configure(state=tk.DISABLED)
            self.git.configure(state=tk.DISABLED)
            self.sql.configure(state=tk.DISABLED)
        else:
            self.basics.configure(state=tk.NORMAL)
            self.oop.configure(state=tk.NORMAL)
            self.pep.configure(state=tk.NORMAL)
            self.structures.configure(state=tk.NORMAL)
            self.alghoritms.configure(state=tk.NORMAL)
            self.git.configure(state=tk.NORMAL)
            self.sql.configure(state=tk.NORMAL)

        self.interview_mode = {
            Theme.BASICS: self.basics_chosen.get(),
            Theme.OOP: self.oop_chosen.get(),
            Theme.PEP8: self.pep_chosen.get(),
            Theme.STRUCTURES: self.structures_chosen.get(),
            Theme.ALGHORITMS: self.alghoritms_chosen.get(),
            Theme.GIT: self.git_chosen.get(),
            Theme.SQL: self.sql_chosen.get(),
            'Freemode': self.freemode_var.get(),
            'Random': self.are_random_questions.get()
        }
        self.set_interview_mode(self.interview_mode)

    def choose_random_interview(self) -> None:
        """Creates a panel for random interview setting."""
        self.choose_random_interview_frame = ctk.CTkFrame(
            self, fg_color=SWAMP_FOREGROUND,
            width=1185,
            height=100
            )
        self.choose_random_interview_frame.grid(
            row=1,
            column=0,
            sticky='n',
            padx=20,
            pady=20
            )

        self.draw_label(
            self.choose_random_interview_frame,
            'Последовательность вопросов'
            )
        self.draw_line(self.choose_random_interview_frame)

        self.random_button_off = ctk.CTkRadioButton(
            self.choose_random_interview_frame,
            value=0,
            text='Вопросы задают последовательно',
            variable=self.are_random_questions,
            fg_color=CHECKBOX_HOVER_COLOR,
            hover_color=CHECKBOX_HOVER_COLOR,
            command=self.add_chosen_theme)
        self.random_button_off.place(x=420, y=40)

        self.random_button_on = ctk.CTkRadioButton(
            self.choose_random_interview_frame,
            value=1,
            text='Вопросы задают случайно',
            variable=self.are_random_questions,
            fg_color=CHECKBOX_HOVER_COLOR,
            hover_color=CHECKBOX_HOVER_COLOR,
            command=self.add_chosen_theme)
        self.random_button_on.place(x=700, y=40)

    def choose_free_mode(self) -> None:
        """Creates a freemode setting."""
        self.choose_free_mode_frame = ctk.CTkFrame(
            self,
            fg_color=SWAMP_FOREGROUND,
            width=1185,
            height=100
            )
        self.choose_free_mode_frame.grid(
            row=2,
            column=0,
            sticky='n',
            padx=20,
            pady=20
            )

        self.draw_label(
            self.choose_free_mode_frame,
            'Свободное перемещение по вопросам'
            )
        self.draw_line(self.choose_free_mode_frame)

        self.freemode_button_on = ctk.CTkRadioButton(
            self.choose_free_mode_frame,
            value=1,
            text='Включить свободный выбор вопросов',
            variable=self.freemode_var,
            fg_color=CHECKBOX_HOVER_COLOR,
            hover_color=CHECKBOX_HOVER_COLOR,
            command=self.add_chosen_theme)
        self.freemode_button_on.place(x=420, y=40)

        self.freemode_button_off = ctk.CTkRadioButton(
            self.choose_free_mode_frame,
            value=0,
            text='Отключить свободный выбор вопросов',
            variable=self.freemode_var,
            fg_color=CHECKBOX_HOVER_COLOR,
            hover_color=CHECKBOX_HOVER_COLOR,
            command=self.add_chosen_theme)
        self.freemode_button_off.place(x=700, y=40)

    def toggle_sounds(self) -> None:
        """Creates a panel to manage a sound volume."""
        self.toggle_sounds_frame = ctk.CTkFrame(
            self,
            fg_color=SWAMP_FOREGROUND,
            width=1185,
            height=100
            )
        self.toggle_sounds_frame.grid(
            row=3,
            column=0,
            sticky='n',
            padx=20,
            pady=20
            )
        self.draw_label(
            self.toggle_sounds_frame,
            'Управление громкостью собеседования'
            )
        self.draw_line(self.toggle_sounds_frame)

        self.sound_scale = ctk.CTkSlider(
            self.toggle_sounds_frame,
            orientation='horizontal',
            from_=0,
            to=100,
            variable=self.sound_volume,
            width=280,
            command=self.transfer_volume_number,
            button_color=CHECKBOX_HOVER_COLOR,
            button_hover_color=CHECKBOX_HOVER_COLOR,
            progress_color=CHECKBOX_HOVER_COLOR)
        self.sound_scale.place(x=420, y=40)
        self.sound_label = ctk.CTkLabel(
            self.toggle_sounds_frame,
            textvariable=self.sound_text
            )
        self.sound_label.place(x=710, y=32)

    def transfer_volume_number(self, value) -> None:
        """Transferring a current volume to the main class."""
        self.sound_text.set(f'Громкость: {self.sound_volume.get()}%')
        self.set_volume(round(int(self.sound_volume.get()) / 100, 1))


class InterviewPassTab(ctk.CTkFrame):
    """Class for interview passing."""
    def __init__(self, parent, themes,
                 database, show_hint_window,
                 get_volume, set_volume,
                 get_current_user, set_notebook_status,
                 get_interview_mode, get_user_progress,
                 update_progress):
        # Setup
        super().__init__(parent)
        self.width = 1200
        self.place(x=0, y=0)
        self.columnconfigure((0, 1), weight=1)
        self.rowconfigure((0, 1), weight=1)

        # The outer functions
        self.question_bank = database
        self.themes = themes
        self.show_hint_window = show_hint_window
        self.get_volume = get_volume
        self.set_volume = set_volume
        self.get_current_user = get_current_user
        self.set_notebook_status = set_notebook_status
        self.get_interview_mode = get_interview_mode
        self.get_user_progress = get_user_progress
        self.update_progress = update_progress

        # Instance vars
        self.current_user = None
        self.interview_mode = {}
        self.question_list = []
        self.user_progress = {}
        self.questions_while_interviewing = deque()
        self.pointer = 0
        self.start_interview_time = datetime.datetime
        self.stop_interview_time = datetime.datetime
        self.button_text = ctk.StringVar(value='Начать собеседование')
        self.question_key = None

        # Flags
        self.is_interview_in_progress = False

        # Context menu for copying text from textbox
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label="Копировать",
            command=lambda: self.focus_get().event_generate("<<Copy>>")
            )

        # Widgets creating
        self.create_interview_frame()
        self.create_control_frame()
        self.create_treeview_frame()

        # Events
        self.context_menu_event_loop(self.theory_textbox)
        self.context_menu_event_loop(self.coding_textbox)
        self.treeview_events()

    def create_interview_frame(self):
        """Creates a panel with:
        - start/stop interview button
        - theory/livecoding textboxes
        - buttons for managing sounds.
        """
        self.interview_frame = ctk.CTkFrame(
            self,
            fg_color=ORANGE_FOREGROUND,
            width=620,
            height=400
            )
        self.interview_frame.grid(row=0, column=0, padx=30, pady=10)

        # first row
        self.begin_button_start = ctk.CTkImage(
            light_image=Image.open('images/start.png').resize((30, 30)),
            dark_image=Image.open('images/start.png').resize((30, 30))
        )
        self.begin_button_stop = ctk.CTkImage(
            light_image=Image.open('images/stop.png').resize((30, 30)),
            dark_image=Image.open('images/stop.png').resize((30, 30))
        )

        self.begin_button = ctk.CTkButton(
            master=self.interview_frame,
            width=300,
            height=40,
            textvariable=self.button_text,
            fg_color=BEGIN_BUTTON_FOREGROUND_COLOR,
            text_color='black',
            hover_color=BEGIN_BUTTON_HOVER_COLOR,
            command=self.begin_interview,
            image=self.begin_button_start)
        self.begin_button.place(x=20, y=20)

        self.replay_button = ctk.CTkButton(
            master=self.interview_frame,
            width=150,
            height=40,
            text='Проиграть вопрос',
            fg_color=SOUNDS_BUTTONS_FOREGROUND,
            hover_color=SOUNDS_BUTTONS_HOVER,
            command=self.speak_theory_question
            )
        self.replay_button.place(x=400, y=20)

        self.mute_button_img_ON = ctk.CTkImage(
            light_image=Image.open('images/sound_ON.png').resize((30, 30)),
            dark_image=Image.open('images/sound_ON.png').resize((30, 30))
        )
        self.mute_button_img_OFF = ctk.CTkImage(
            light_image=Image.open('images/sound_OFF.png').resize((30, 30)),
            dark_image=Image.open('images/sound_OFF.png').resize((30, 30))
        )

        self.mute_button = ctk.CTkButton(
            master=self.interview_frame,
            width=40,
            height=40,
            text='',
            fg_color=SOUNDS_BUTTONS_FOREGROUND,
            hover_color=SOUNDS_BUTTONS_HOVER,
            image=self.mute_button_img_ON,
            command=self.mute_sound)
        self.mute_button.place(x=560, y=20)

        ctk.CTkLabel(
            master=self.interview_frame,
            text='Теоретический вопрос',
            font=('Calibri', 25)).place(x=20, y=75)

        self.theory_textbox = ctk.CTkTextbox(
            master=self.interview_frame,
            width=580,
            height=100,
            font=('Calibri', 18)
        )
        self.theory_textbox.place(x=20, y=120)

        ctk.CTkLabel(
            master=self.interview_frame,
            text='Live coding',
            font=('Calibri', 25)).place(x=20, y=240)

        self.coding_button = ctk.CTkButton(
            master=self.interview_frame,
            width=150,
            height=28,
            text='Проиграть вопрос Live coding',
            fg_color=SOUNDS_BUTTONS_FOREGROUND,
            hover_color=SOUNDS_BUTTONS_HOVER,
            command=self.speak_livecoding,)
        self.coding_button.place(x=160, y=242)

        self.coding_textbox = ctk.CTkTextbox(
            master=self.interview_frame,
            width=580,
            height=100,
            font=('Calibri', 18)
        )
        self.coding_textbox.place(x=20, y=280)

    def create_control_frame(self):
        """Creates a panel with:
        - correct answer button
        - wrong answer button
        - show the answer button.
        """
        self.control_frame = ctk.CTkFrame(
            self,
            fg_color=ORANGE_FOREGROUND,
            width=620,
            height=200
            )
        self.control_frame.grid(row=1, column=0)

        self.positive_button = ctk.CTkButton(
            master=self.control_frame,
            width=260,
            height=70,
            text='Я правильно ответил на вопрос',
            fg_color=POSITIVE_BUTTON_FOREGROUND,
            hover_color=POSITIVE_BUTTON_HOVER,
            command=self.answer_correctly,
        )
        self.positive_button.place(x=20, y=20)

        self.negative_button = ctk.CTkButton(
            master=self.control_frame,
            width=260,
            height=70,
            text='Я не знаю, следующий вопрос',
            fg_color=NEGATIVE_BUTTON_FOREGROUND,
            hover_color=NEGATIVE_BUTTON_HOVER,
            command=self.answer_wrong,
        )
        self.negative_button.place(x=340, y=20)

        self.answer_button = ctk.CTkButton(
            master=self.control_frame,
            width=580,
            height=70,
            text='Посмотреть ответ на вопрос',
            fg_color=ANSWER_BUTTON_FOREGROUND,
            hover_color=ANSWER_BUTTON_HOVER,
            command=self.push_hint_button
        ).place(x=20, y=110)

    def create_treeview_frame(self):
        """Creates a question treeview."""
        # The frame which has all the widgets
        self.control_frame = ctk.CTkFrame(
            self,
            fg_color=ORANGE_FOREGROUND,
            width=530,
            height=615
            )
        self.control_frame.grid(row=0, column=1, rowspan=2, pady=10)

        # Question tree
        self.question_tree = ttk.Treeview(
            master=self.control_frame,
            selectmode='none'
        )

        self.question_tree.heading(
            '#0',
            text='Темы и вопросы собеседования',
            anchor=tk.W
            )

        # adding data
        for theme_id, theme_title in self.themes.items():
            self.question_tree.insert(
                '',
                tk.END,
                text=theme_title,
                iid=theme_id,
                open=False
                )

        # adding children of first node
        for data in self.question_bank:
            self.question_tree.insert(
                '',
                tk.END,
                text=f'Вопрос {data[0] - 7}. {data[2]}',
                iid=data[0],
                open=False
                )
            match data[0]:
                case num if qt.BASIC_FIRST_QUESTION <= num <= qt.BASIC_LAST_QUESTION:
                    self.question_tree.move(data[0], 0, data[1])
                case num if qt.OOP_FIRST_QUESTION <= num <= qt.OOP_LAST_QUESTION:
                    self.question_tree.move(data[0], 1, data[1])
                case num if qt.PEP8_FIRST_QUESTION <= num <= qt.PEP8_LAST_QUESTION:
                    self.question_tree.move(data[0], 2, data[1])
                case num if qt.STRUCTURES_FIRST_QUESTION <= num <= qt.STRUCTURES_LAST_QUESTION:
                    self.question_tree.move(data[0], 3, data[1])
                case num if qt.ALGHORITMS_FIRST_QUESTION <= num <= qt.ALGHORITMS_LAST_QUESTION:
                    self.question_tree.move(data[0], 4, data[1])
                case num if qt.GIT_FIRST_QUESTION <= num <= qt.GIT_LAST_QUESTION:
                    self.question_tree.move(data[0], 5, data[1])
                case num if qt.SQL_FIRST_QUESTION <= num <= qt.SQL_LAST_QUESTION:
                    self.question_tree.move(data[0], 6, data[1])

        self.question_tree.place(x=20, y=20, width=490, height=580)

        self.scroll_question_tree = ctk.CTkScrollbar(
            master=self.control_frame,
            orientation='vertical',
            command=self.question_tree.yview)
        self.question_tree.configure(
            yscrollcommand=self.scroll_question_tree.set
            )
        self.scroll_question_tree.place(x=500, y=20, relheight=0.945)

        self.style = ttk.Style()
        self.style.configure('Treeview.Heading', font=('Calibri', 18))
        self.style.configure('Treeview', font=('Calibri', 12))

    def begin_interview(self):
        """Manages interview passing.
        - Loads essential information
        - Check user's existance
        - Updates DB data.
        """
        # Turn ON answers buttons
        self.positive_button.configure(state='normal')
        self.negative_button.configure(state='normal')

        # Loading data
        self.current_user = self.get_current_user()
        self.interview_mode = self.get_interview_mode()

        if not self.is_interview_in_progress:
            self.start_interview_time = self.start_interview_time.today()
            update_last_enter_date(
                self.current_user,
                self.start_interview_time
                )
            self.begin_button.configure(
                image=self.begin_button_stop
                )
            self.button_text.set('Закончить собеседование')
            self.is_interview_in_progress = True
            self.set_notebook_status('disabled')
            if not self.current_user:
                CTkMessagebox(
                    title='Предупреждение',
                    message='Вы не выбрали пользователя. Статистика не ведется'
                    )
                self.question_tree.configure(selectmode='browse')
                self.open_chosen_themes()
                self.set_pointer_at_first_question()
            else:
                if self.interview_mode['Freemode']:
                    self.question_tree.configure(selectmode='browse')
                else:
                    self.question_tree.configure(selectmode='none')
                self.open_chosen_themes()
                self.set_pointer_at_first_question()
        else:
            self.stop_interview()

    def stop_interview(self):
        """Stops the interview updating user progress."""
        self.stop_interview_time = self.stop_interview_time.today()
        self.update_interview_duration()
        self.is_interview_in_progress = False
        self.set_notebook_status('normal')
        self.begin_button.configure(image=self.begin_button_start)
        self.button_text.set('Начать собеседование')
        self.question_tree.configure(selectmode='none')
        self.question_list.clear()
        self.questions_while_interviewing.clear()
        self.positive_button.configure(state='disabled')
        self.negative_button.configure(state='disabled')
        if self.current_user:
            self.update_progress()

    def update_interview_duration(self):
        """Updates an interview duration on DB."""
        if self.current_user:
            initial_duration = get_user_interview_duration(self.current_user)
            seconds_left = count_interview_duration(
                self.start_interview_time,
                self.stop_interview_time
                )
            result_duration = initial_duration + seconds_left
            update_interview_duration(self.current_user, result_duration)

    def open_chosen_themes(self):
        """Opens the themes in the question tree which were chosen."""
        for theme in self.question_tree.get_children():
            self.question_tree.item(theme, open=False)
        themes_status = tuple(self.interview_mode.values())[:7]
        open_themes = [
            theme_index
            for theme_index, is_chosen in enumerate(themes_status) if is_chosen
            ]
        if not open_themes:
            CTkMessagebox(
                title='Ошибка',
                message="Вы не выбрали ни одной темы",
                icon="cancel",
                option_1="Отлично"
                )
            self.stop_interview()
        for theme in open_themes:
            self.question_tree.item(theme, open=True)
        self.generate_question_list(open_themes)

    def generate_question_list(self, open_themes):
        """Generares a question list for this session."""
        self.user_progress = self.get_user_progress()
        user_right_answer = {
            question_number
            for question_number, is_right
            in self.user_progress.items() if is_right
            }

        for theme in open_themes:
            match theme:
                case 0:
                    self.question_list += [
                        question_number
                        for question_number
                        in range(qt.BASIC_FIRST_QUESTION,
                                 qt.BASIC_LAST_QUESTION + 1)
                        ]
                case 1:
                    self.question_list += [
                        question_number
                        for question_number
                        in range(qt.OOP_FIRST_QUESTION,
                                 qt.OOP_LAST_QUESTION + 1)
                        ]
                case 2:
                    self.question_list += [
                        question_number
                        for question_number
                        in range(qt.PEP8_FIRST_QUESTION,
                                 qt.PEP8_LAST_QUESTION + 1)
                        ]
                case 3:
                    self.question_list += [
                        question_number
                        for question_number
                        in range(qt.STRUCTURES_FIRST_QUESTION,
                                 qt.STRUCTURES_LAST_QUESTION + 1)
                        ]
                case 4:
                    self.question_list += [
                        question_number
                        for question_number
                        in range(qt.ALGHORITMS_FIRST_QUESTION,
                                 qt.ALGHORITMS_LAST_QUESTION + 1)
                        ]
                case 5:
                    self.question_list += [
                        question_number
                        for question_number
                        in range(qt.GIT_FIRST_QUESTION,
                                 qt.GIT_LAST_QUESTION + 1)
                        ]
                case 6:
                    self.question_list += [
                        question_number
                        for question_number
                        in range(qt.SQL_FIRST_QUESTION,
                                 qt.SQL_LAST_QUESTION + 1)
                        ]
        self.question_list = [
            question_number
            for question_number
            in self.question_list if question_number not in user_right_answer
            ]
        if self.interview_mode['Random']:
            random.shuffle(self.question_list)

    # CORRECT OR WRONG ANSWER SECTION
    def answer_correctly(self):
        """Manages user progress when
        user has answered correctrly.
        """
        try:
            if not self.interview_mode['Freemode']:
                self.turn_to_green()
                index = self.questions_while_interviewing.popleft()
                self.question_tree.selection_set(
                    (str(self.questions_while_interviewing[0]), )
                    )
                self.question_tree.see(
                    (str(self.questions_while_interviewing[0]), )
                    )
                self.speak_theory_question()
                self.user_progress[index] = True
                update_user_progress(self.current_user, self.user_progress)
            else:
                self.turn_to_green()
                self.user_progress[self.question_key + 8] = True
                update_user_progress(self.current_user, self.user_progress)
        except IndexError:
            self.stop_interview()
            CTkMessagebox(
                title='Вы ответили на все вопросы',
                message="Поздравляем! Вы ответили на все вопросы данной темы",
                icon="check",
                option_1="Отлично"
                )

    def answer_wrong(self):
        """Manages user progress when
        user has answered wrong.
        """
        if not self.interview_mode['Freemode']:
            self.turn_to_red()
            self.questions_while_interviewing.rotate(-1)
            self.question_tree.selection_set(
                (str(self.questions_while_interviewing[0]), )
                )
            self.question_tree.see(
                (str(self.questions_while_interviewing[0]), )
                )
            self.speak_theory_question()
        else:
            self.turn_to_red()

    def set_pointer_at_first_question(self):
        """Shows the first question when interview has started."""
        for question_number in self.question_list:
            self.questions_while_interviewing.append(question_number)
        try:
            self.question_tree.selection_set(
                (str(self.questions_while_interviewing[0]), )
                )
            self.question_tree.see(
                (str(self.questions_while_interviewing[0]), )
                )
            self.speak_theory_question()
        except IndexError:
            pass

    def set_color_for_user_progress(self):
        """Turns to green or red user's answer."""
        # Set zero (white) color in everywhere
        for question_number in range(qt.BASIC_FIRST_QUESTION,
                                     qt.SQL_LAST_QUESTION + 1):
            self.question_tree.item(
                question_number,
                tags=(WHITE, ),
                values=(WHITE, )
                )
            self.question_tree.tag_configure(WHITE, background=WHITE)

        # Get user progress
        self.user_progress = self.get_user_progress()

        # Get color of questions according user progress
        for question_number, is_right in self.user_progress.items():
            if is_right:
                self.question_tree.item(
                    question_number,
                    tags=(GREEN, ), values=(GREEN, )
                    )
                self.question_tree.tag_configure(GREEN, background=GREEN)

    def turn_to_green(self):
        """Turns user's answer to green."""
        if isinstance(self.question_key, int):
            self.question_tree.item(
                self.question_key + 8,
                tags=(GREEN, ),
                values=(GREEN, )
                )
            self.question_tree.tag_configure(GREEN, background=GREEN)

    def turn_to_red(self):
        """Turns user's answer to red."""
        if isinstance(self.question_key, int):
            self.question_tree.item(
                self.question_key + 8, tags=(RED, ), values=(RED, )
                )
            self.question_tree.tag_configure(RED, background=RED)

    def push_hint_button(self):
        """Shows the PDF-file with correct answer."""
        if isinstance(self.question_key, int):
            self.show_hint_window(
                filepath=(
                    f'knowledge/{self.question_bank[self.question_key][5]}.pdf'
                    ),
                page_number=self.question_bank[self.question_key][6]
                )

    # SOUNDS AND VOLUME SECTION
    def mute_sound(self):
        """Mutes every sounds in the app."""
        if self.get_volume():
            self.set_volume(0)
        else:
            self.set_volume(0.5)

    def prepare_livecoding(self):
        """Prepares the text from livecoding textbox to speech (TTS)."""
        try:
            if self.get_volume():
                engine = pyttsx3.init()
                engine.setProperty('volume', self.get_volume())
                engine.say(self.question_bank[
                    self.questions_while_interviewing[0] - 8][4])
                engine.runAndWait()
        except RuntimeError:
            pass

    def prepare_theory_question(self):
        """Prepares the text from theory textbox to speech (TTS)."""
        try:
            if self.get_volume():
                engine = pyttsx3.init()
                engine.setProperty('volume', self.get_volume())
                engine.say(self.question_bank[
                    self.questions_while_interviewing[0] - 8][3])
                engine.runAndWait()
        except RuntimeError:
            pass

    def speak_theory_question(self):
        """Plays theory question."""
        threading.Thread(target=self.prepare_theory_question).start()

    def speak_livecoding(self):
        """Plays livecoding question."""
        threading.Thread(target=self.prepare_livecoding).start()

    # EVENTS SECTION
    def context_menu_event_loop(self, text_box):
        """Allows to use CTRL-C or RMB to copy the text from a textbox."""
        text_box.bind(
            "<Button-3>",
            lambda event: self.context_menu.post(event.x_root, event.y_root)
            )
        text_box.bind(
            "<Control-c>",
            lambda event: self.copy_text
            )

    def treeview_events(self):
        """Allows to select items for question treeview."""
        self.question_tree.bind('<<TreeviewSelect>>', self.item_select)

    def insert_question_in_textfield(self, question_key):
        """Inserts the questions to the textboxes."""
        if question_key is not None:
            self.theory_textbox.delete('1.0', 'end')
            self.coding_textbox.delete('1.0', 'end')
            self.theory_textbox.insert('1.0',
                                       self.question_bank[question_key][3])
            self.coding_textbox.insert('1.0',
                                       self.question_bank[question_key][4])
        else:
            self.theory_textbox.delete('1.0', 'end')
            self.coding_textbox.delete('1.0', 'end')

    def item_select(self, event):
        """Allows to select items from question tree."""
        for i in self.question_tree.selection():
            self.question_key = (
                self.question_tree.item(i)['text'].split(
                    '. ')[0].strip('Вопрос ')
                )
            self.question_key = (
                int(self.question_key) - 1
                if self.question_key.isdigit() else None
                )
            self.insert_question_in_textfield(self.question_key)

    def copy_text(event):
        """Allows to copy a text from textboxes."""
        widget = event.widget
        selected_text = widget.clipboard_get()
        if widget.tag_ranges("sel"):
            selected_text = widget.get("sel.first", "sel.last")
        widget.clipboard_clear()
        widget.clipboard_append(selected_text)


class CreateNewUser(ctk.CTkToplevel):
    """Class for a window creating a new user."""
    def __init__(self, title, update_combobox):
        # Setup
        super().__init__()
        self.title(title)
        self.geometry('390x160')
        self.resizable(False, False)
        self.iconbitmap(default='images/icon.ico')
        if platform.startswith("win"):
            self.after(200, lambda: self.iconbitmap("images/icon.ico"))
        self.update_combobox = update_combobox

        # Vars
        self.user_name = ctk.StringVar()
        self.error_message = ctk.StringVar(value='')

        # Widgets
        self.frame = ctk.CTkFrame(
            self,
            width=350,
            height=110,
            fg_color=NEW_USER_WINDOW_FOREGROUND
            )
        self.frame.pack(side='top', expand=True, fill='both', padx=10, pady=10)
        self.frame.rowconfigure((0, 1, 2, 3), weight=1)
        self.frame.columnconfigure((0, 1), weight=1)

        self.label = ctk.CTkLabel(
            self.frame,
            text='Создайте имя пользователя:'
            )
        self.label.grid(row=0, column=0, sticky='ws', padx=10)
        self.enter = ctk.CTkEntry(
            self.frame,
            width=350,
            textvariable=self.user_name
            )
        self.enter.grid(row=1, column=0, sticky='wn', padx=10, columnspan=2)
        self.error_label = ttk.Label(
            self.frame,
            textvariable=self.error_message,
            background=ERROR_COLOR
            )
        self.error_label.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky='wn',
            padx=10
            )
        self.save_button = ctk.CTkButton(
            self.frame,
            text='Создать',
            command=self.add_to_db
            )
        self.save_button.grid(row=3, column=0, sticky='wn', padx=10)
        self.cancel_button = ctk.CTkButton(
            self.frame,
            text='Отмена',
            command=self.close_the_window
            )
        self.cancel_button.grid(row=3, column=1, sticky='en', padx=10)

    def close_the_window(self):
        """Destroys the window."""
        self.destroy()

    def add_to_db(self):
        """Adds a new user to DB provided he passes a validation."""
        current_user = self.user_name.get()
        if is_name_empty(current_user):
            self.error_label.config(background='red')
            self.error_message.set(ValidResponse.EMPTY_NAME)
            self.set_timer(3)
        elif is_name_too_short(current_user):
            self.error_label.config(background='red')
            self.error_message.set(ValidResponse.SHORT_NAME)
            self.set_timer(3)
        elif is_name_too_long(current_user):
            self.error_label.config(background='red')
            self.error_message.set(ValidResponse.NAME_TOO_LONG)
            self.set_timer(3)
        elif has_name_first_wrong_symbol(current_user):
            self.error_label.config(background='red')
            self.error_message.set(ValidResponse.WRONG_FIRST_SYMBOL)
            self.set_timer(3)
        elif has_name_wrong_symbols(current_user):
            self.error_label.config(background='red')
            self.error_message.set(ValidResponse.WRONG_SYMBOLS)
            self.set_timer(3)
        elif is_user_already_exists(current_user):
            self.error_label.config(background='red')
            self.error_message.set(ValidResponse.USER_ALREADY_EXISTS)
            self.set_timer(3)
        else:
            create_new_user(self.user_name.get())
            self.update_combobox()
            CommandTimer(1, self.destroy, self.error_label, self.error_message)

    def set_timer(self, delay):
        """Creates a delay for showing message."""
        MessageTimer(delay, self.error_message, self.error_label)


class HintWindow(ctk.CTkToplevel):
    """Class for a new window showing a right answer."""
    def __init__(self, title, filepath, current_page):
        # Setup
        super().__init__()
        self.title(title)
        self.geometry('900x800+440+180')
        self.resizable(False, False)
        self.iconbitmap('images/icon.ico')
        if platform.startswith("win"):
            self.after(200, lambda: self.iconbitmap("images/icon.ico"))
        self.rowconfigure((0, 1), weight=1)
        self.columnconfigure((0, 1), weight=1)

        # The outer functions
        self.file = filepath
        self.current_page = current_page

        # Vars
        self.numPages = None
        self.pages_amount = ctk.StringVar()

        # Top Frame
        self.top_frame = ctk.CTkFrame(self, width=850, height=700)
        self.top_frame.grid(row=0, column=0)

        # Bottom Frame
        self.bottom_frame = ctk.CTkFrame(
            master=self,
            width=580,
            height=50,
            fg_color='transparent'
            )
        self.bottom_frame.grid(row=1, column=0)
        self.bottom_frame.rowconfigure((0,), weight=1)
        self.bottom_frame.columnconfigure((0, 1, 2), weight=1)

        # Vertical Scrolbar
        self.scrolly = ctk.CTkScrollbar(self.top_frame, orientation='vertical')
        self.scrolly.grid(row=0, column=1, sticky='ns')

        # Show PDF
        self.output = ctk.CTkCanvas(
            self.top_frame,
            bg=PDF_OUTPUT_COLOR,
            width=880,
            height=700
            )
        self.output.configure(yscrollcommand=self.scrolly.set)
        self.output.grid(row=0, column=0)
        self.scrolly.configure(command=self.output.yview)
        self.output.bind(
            '<MouseWheel>', lambda event: self.output.yview_scroll(
                -1*(event.delta//120), "units")
                )

        # Buttons and page label
        self.upbutton = ctk.CTkButton(
            master=self.bottom_frame,
            text='Предыдущая страница',
            command=self.previous_page)
        self.upbutton.grid(row=0, column=0, padx=5, pady=5)
        self.downbutton = ctk.CTkButton(
            master=self.bottom_frame,
            text='Следующая страница',
            command=self.next_page
            )
        self.downbutton.grid(row=0, column=1, pady=5)
        self.page_label = ctk.CTkLabel(
            master=self.bottom_frame,
            textvariable=self.pages_amount
            )
        self.page_label.grid(row=0, column=2, padx=5)

        if self.file:
            self.miner = PDFMiner(self.file)
            data, numPages = self.miner.get_metadata()
            if numPages:
                self.numPages = numPages
                self.display_page()

    def display_page(self):
        """Shows a particular page."""
        if 0 <= self.current_page < self.numPages:
            self.img_file = self.miner.get_page(self.current_page)
            self.output.create_image(0, 0, anchor='nw', image=self.img_file)
            self.stringified_current_page = self.current_page + 1
            self.pages_amount.set(
                f'Страница: {self.stringified_current_page} из {self.numPages}'
                )
            region = self.output.bbox(tk.ALL)
            self.output.configure(scrollregion=region)

    def next_page(self):
        """Turns to the next page."""
        if self.current_page <= self.numPages - 1:
            self.current_page += 1
            self.display_page()

    def previous_page(self):
        """Turns to the previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.display_page()


class PDFMiner:
    """Class for rendering PDF-files."""
    def __init__(self, filepath):
        self.filepath = filepath
        self.pdf = fitz.open(self.filepath)
        self.first_page = self.pdf.load_page(0)
        self.width, self.height = (
            self.first_page.rect.width,
            self.first_page.rect.height
            )
        self.zoom = 1.5

    def get_metadata(self):
        metadata = self.pdf.metadata
        numPages = self.pdf.page_count
        return metadata, numPages

    def get_page(self, page_num):
        page = self.pdf.load_page(page_num)
        if self.zoom:
            mat = fitz.Matrix(self.zoom, self.zoom)
            pix = page.get_pixmap(matrix=mat)
        else:
            pix = page.get_pixmap()
        px1 = fitz.Pixmap(pix, 0) if pix.alpha else pix
        imgdata = px1.tobytes("ppm")
        return PhotoImage(data=imgdata)

    def get_text(self, page_num):
        page = self.pdf.load_page(page_num)
        text = page.getText('text')
        return text


if __name__ == '__main__':
    create_db()
    ctk.set_appearance_mode("Light")
    main_window = Main(APP_NAME, APP_RESOLUTION)
    main_window.mainloop()
