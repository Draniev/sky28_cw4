from enum import Enum

from rich import print

from hh_vacancyapi import HHVacancyAPI
from load_env import SJ_API_KEY
from saveload import JSONSaveLoadVacancies
from sj_vacancyapi import SJVacancyAPI
from vacancy import Vacancy
from vacancyapi import VacancyApi


class UIState(Enum):
    IDLE = 'Ожидаем начала работы'
    LOAD_FILE = 'Ожидаем загрузку вакансий из файла'
    API_SEARCH0 = 'Выбираем сайт для поиска вакансий по АПИ'
    API_SEARCH1 = 'Загружаем критерии поиска вакансий'
    VACANCY = 'Режим работы с загруженными вакансиями'
    EXIT = 'Выключаемся'


class UserInterface:

    def __init__(self):
        self.__state = UIState.IDLE
        self.hh_api = HHVacancyAPI()
        self.sj_api = SJVacancyAPI(SJ_API_KEY)
        self.apies: list[VacancyApi] = []
        self.vacancies: list[Vacancy] = []
        self.print_qty: int = 10  # количество объектов на печать
        self.loader = JSONSaveLoadVacancies()

    def start(self):
        is_exit = False

        while not is_exit:
            is_exit = self.__hello_ui()

        print('Досвидули, я закрываюсь')

    def __hello_ui(self) -> bool:

        match self.__state:
            case UIState.IDLE:
                is_exit = self.__idle_input()
            case UIState.LOAD_FILE:
                is_exit = self.__load_file()
            case UIState.API_SEARCH0:
                is_exit = self.__search0_input()
            case UIState.API_SEARCH1:
                is_exit = self.__find_vacancy_ui()
            case UIState.VACANCY:
                is_exit = self.__working_with_vacancy()
            case _:
                is_exit = True  # В любой не понятной ситуации - досвидули!

        # print(self.__state)
        # print(f'is_exit: {is_exit}')
        return is_exit

    def __idle_input(self) -> bool:

        print('(1) Поработать с локальными файлами '
              '\n(2) найти новые вакансии, '
              '\n(9, exit) выйти?')

        user_input = input('Выберите действие: 1, 2 или 9 >> ')

        match user_input:
            case '1':
                self.__state = UIState.LOAD_FILE
            case '2':
                self.__state = UIState.API_SEARCH0
            case '9' | 'exit':
                return True  # Завершение и выход

        return False

    def __load_file(self) -> bool:

        filename = input('(8, back) назад или выйти (9, exit)\n'
                         'Имя файла для загрузки. "Enter" - по умолчанию. >> ')

        match filename:
            case '8' | 'back':  # Возврат на предыдуший шаг
                self.__state = UIState.IDLE
                return False
            case '9' | 'exit':
                return True  # Завершение и выход

        try:
            self.vacancies = []
            if len(filename) == 0:
                self.vacancies = self.loader.loadfile()
            else:
                self.vacancies = self.loader.loadfile(filename)

            print(f'Из файла загружено {len(self.vacancies)} вакансий')
            self.__state = UIState.VACANCY

        except FileNotFoundError:
            print('Файл повреждён или не найден. Попробуем еще раз?')

        return False  # Продолжаем работу в цикле

    def __safe_to_file(self, vacancies: list[Vacancy]) -> bool:

        filename = input('(8, back) назад\n'
                         'Введите имя файла. "Enter" - по умолчанию. >> ')

        match filename:
            case '8' | 'back':  # Возврат на предыдуший шаг
                return False

        if len(filename) == 0:
            self.loader.savefile(vacancies)
        else:
            self.loader.savefile(vacancies, f'{filename}.json')

        print(f'Записано в файл {len(self.vacancies)} вакансий')

        return False  # Продолжаем работу в цикле

    def __search0_input(self) -> bool:

        print('Поискать \n(1) на HeadHunter '
              '\n(2) на SuperJob '
              '\n(3) на всех доступных платформах '
              '\n(8, back) назад или выйти (9, exit)?')

        user_input = input('Выберите действие: 0, 1, 2 или 8, 9 >> ')

        match user_input:
            case '1':  # Поиск на ХХ
                self.apies = [self.hh_api]
            case '2':  # Поиск на SJ
                self.apies = [self.sj_api]
            case '3':  # Поиск на обоих платформах
                self.apies = [self.hh_api, self.sj_api]
            case '8' | 'back':  # Возврат на предыдуший шаг
                self.__state = UIState.IDLE
                return False
            case '9' | 'exit':
                return True  # Завершение и выход

        self.__state = UIState.API_SEARCH1
        return False

    def __find_vacancy_ui(self) -> bool:

        keyword = input('(8, back) назад или выйти (9, exit)\n'
                        'Ключевое слово для поиска: ')

        match keyword:
            case '8' | 'back':  # Возврат на предыдуший шаг
                self.__state = UIState.API_SEARCH0
                return False
            case '9' | 'exit':
                return True  # Завершение и выход

        salary = input('(8, back) назад или выйти (9, exit)\n'
                       'Примерная зарплата в RUR (0 если не важно): ')

        match salary:
            case '0':
                salary = None
            case '8' | 'back':  # Возврат на предыдуший шаг
                self.__state = UIState.API_SEARCH0
                return False
            case '9' | 'exit':
                return True  # Завершение и выход
            case _:
                salary = int(salary) if salary.isnumeric() else None

        self.vacancies = []
        for api in self.apies:
            print(f'Начинаем парсинг {api} '
                  f'для вакансий по ключу "{keyword.upper()}"')
            vacancies = api.get_vacancy(keyword, salary)
            print(f'Найдено {len(vacancies)} с помощью {api}')
            self.vacancies.extend(vacancies)

        print(f'Используя {len(self.apies)} апи '
              f'получено {len(self.vacancies)} вакансий')
        self.__state = UIState.VACANCY
        return False  # Продолжаем работу в цикле

    def __working_with_vacancy(self) -> bool:
        """
        Пользовательский интерфейс для работы с сохранённым (загруженным)
        в памятя списком вакансий. Доступна фильтрация, всякий вывод и пр.
        При желании тут можно было бы много всего придумать...
        """

        print('(0) Установить кол-во вакансий в выдаче (деф. 10)'
              '\n(1) показать первые N вакансий'
              '\n(2) отсортировать по з/п по уменьшению'
              '\n(3) отсортировать по з/п по увеличению'
              '\n(4) отобрать вакансии по городу'
              '\n(5) отобрать вакансии по ключевому слову'
              '\n(s) сохранить вакансии в файл'
              '\n(9, exit) выйти?')
        action = input('Выберите действие: 0-6, x, s, a, 9 >> ')

        match action:
            case '0':  # Установить отображение N на страницу
                self.__set_print_qty()
            case '1':  # Напечатать первый N вакансий
                self.__print_per_page()
            case '2':  # Отсортировать по уменьшинию
                self.__sort_by_salary(True)
            case '3':  # Отсортировать по увеличению
                self.__sort_by_salary()
            case '4':
                self.__filter_city()
            case '5':
                self.__filter_word()
            case 's':
                self.__safe_to_file(self.vacancies)
            case '9' | 'exit':
                return True  # Завершение и выход

        return False

    def __set_print_qty(self) -> None:
        qty = input('Укажите кол-во объектов для вывода на печать: ')
        try:
            qty = int(qty)
            self.print_qty = qty
        except Exception:
            print(f'Что-то пошло не так, предыдущее значение '
                  f'({self.print_qty}) не изменилось')

    def __print_vacancies_page(self, page: int = 0) -> None:
        print(f'Объекты вакансий с {page * self.print_qty + 1} по '
              f'{page * self.print_qty + self.print_qty}')
        for i in range(self.print_qty):
            print(self.vacancies[page * self.print_qty + i].__str__())
        print('\n[bold]#################[/bold]')

    def __print_per_page(self) -> None:
        # Тут мне очень лень возиться с возможной "последней"
        # страницей, которая может оказаться не полной, так
        # что позволю себе от неё избавиться. Тем более в задаче
        # подобного вообще не было.
        pages = len(self.vacancies) // self.print_qty
        for i in range(pages):
            self.__print_vacancies_page(i)
            is_next = input('Enter -> дальше, Any simbol -> стоп >> ')
            if len(is_next) != 0:
                break

    def __sort_by_salary(self, reverse=False) -> None:
        self.vacancies.sort(reverse=reverse)

    def __filter_city(self) -> bool:

        city = input('(8, back) назад\n'
                     'Введите город для выбоорки >> ')

        match city:
            case '8' | 'back':  # Возврат на предыдуший шаг
                return False
            case _:
                pass

        filtered = filter(lambda x: x.area_name == city, self.vacancies)
        self.vacancies = list(filtered)

        return True  # Продолжаем работу в цикле

    def __filter_word(self) -> bool:

        key = input('(8, back) назад\n'
                    'Введите ключ для фильтрации выборки >> ')

        match key:
            case '8' | 'back':  # Возврат на предыдуший шаг
                return False
            case _:
                pass

        filtered = filter(lambda x: key in (x.name,
                                            x.description,
                                            x.area_name,
                                            ),
                          self.vacancies)
        self.vacancies = list(filtered)

        return True  # Продолжаем работу в цикле
