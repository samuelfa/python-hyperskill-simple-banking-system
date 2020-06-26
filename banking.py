import sqlite3
import random
from string import digits


class CreditCard:
    def __init__(self, number, pin, primary_key=None, balance=0):
        self.number = number
        self.pin = pin
        self.balance = balance
        self.id = primary_key

    def add_income(self, money: int):
        self.balance += money

    def sub_income(self, money: int):
        self.balance -= money


class Repository:
    def __init__(self):
        self.connection = sqlite3.connect('card.s3db')
        self.create_table()

    def __del__(self):
        self.connection.close()

    def create_table(self):
        self.connection.execute('''
        create table if not exists card (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            pin TEXT,
            balance INTEGER DEFAULT 0
        )
        ''')

    def find_one_by_number(self, one_number: str):
        cursor = self.connection.cursor()
        cursor.execute('''
        select * from card where number = ?
        ''', [one_number])
        data = cursor.fetchone()
        if data is None:
            return None

        return CreditCard(data[1], data[2], data[0], data[3])

    def create(self, credit_card: CreditCard):
        cursor = self.connection.cursor()
        cursor.execute('''
        insert into card(number, pin, balance) values(?, ?, ?)
        ''', [credit_card.number, credit_card.pin, credit_card.balance])
        credit_card.id = cursor.lastrowid
        self.connection.commit()

    def delete(self, credit_card: CreditCard):
        self.connection.execute('''
        delete from card where id = ?
        ''', [credit_card.id])
        self.connection.commit()

    def add_income(self, credit_card: CreditCard, income: int):
        credit_card.add_income(income)
        self.connection.execute('''
        update card set balance = balance + ? where id = ?
        ''', [income, credit_card.id])
        self.connection.commit()

    def transfer_money(self, from_credit_card: CreditCard, to_credit_card: CreditCard, money: int):
        to_credit_card.sub_income(money)
        to_credit_card.add_income(money)
        self.connection.execute('''
        update card set balance = balance - ? where id = ?
        ''', [money, from_credit_card.id])
        self.connection.execute('''
        update card set balance = balance + ? where id = ?
        ''', [money, to_credit_card.id])
        self.connection.commit()


class ActionInterface:
    def id(self) -> int:
        pass

    def run(self) -> None:
        pass

    def option(self) -> None:
        pass


class LuhnAlgorithm:
    @staticmethod
    def generate_checksum(number) -> str:
        numbers = list(map(int, list(number)))
        total = len(numbers)

        for num in range(0, total, 2):
            numbers[num] *= 2

        for num in range(total):
            if numbers[num] > 9:
                numbers[num] -= 9

        remain = sum(numbers)

        remain = remain % 10
        if remain == 0:
            return "0"

        return str(10 - remain)


class CreateAccount(ActionInterface):
    def __init__(self, repository: Repository):
        self.id = 1
        self.repository = repository
        self.algorithm = LuhnAlgorithm()

    def run(self) -> None:
        credit_card = self.generate_credit_card()
        self.repository.create(credit_card)
        self.welcome(credit_card)

    def option(self) -> None:
        print(f'{self.id}. Create an account')

    def generate_credit_card(self) -> CreditCard:
        iin = self.get_issuer_identification_number()
        account = self.generate_customer_account()
        number = ''.join([iin, account])
        checksum = self.algorithm.generate_checksum(number)
        number = ''.join([iin, account, checksum])

        pin = self.generate_pin()

        return CreditCard(number, pin)

    @staticmethod
    def welcome(credit_card: CreditCard) -> None:
        print('Your card has been created')
        print('Your card number:')
        print(credit_card.number)
        print('Your card PIN:')
        print(credit_card.pin)

    @staticmethod
    def get_major_industry_identifier() -> str:
        return "4"

    def get_issuer_identification_number(self) -> str:
        mii = self.get_major_industry_identifier()
        numbers = ["0" for _ in range(5)]
        numbers = [mii, *numbers]
        return ''.join(numbers)

    @staticmethod
    def generate_customer_account() -> str:
        numbers = [random.choice(digits) for _ in range(9)]
        return ''.join(numbers)

    @staticmethod
    def generate_pin() -> str:
        numbers = [random.choice(digits) for _ in range(4)]
        return ''.join(numbers)


class LogIntoAccount(ActionInterface):
    def __init__(self, repository: Repository):
        self.id = 2
        self.repository = repository
        self.algorithm = LuhnAlgorithm()

    def run(self):
        print('Enter your card number:')
        number = input()
        print('Enter your PIN:')
        pin = input()

        credit_card = self.login(number, pin)
        if not credit_card:
            print('Wrong vard number or PIN!')
        else:
            print('You have successfully logged in!')
            BankSystem.logged = credit_card

    def option(self) -> None:
        print(f'{self.id}. Log into account')

    def login(self, number, pin):
        if len(number) != 16 \
                or len(pin) != 4:
            return None

        check_sum = number[-1]
        calculated_check_sum = self.algorithm.generate_checksum(number[0:-1])

        if check_sum != calculated_check_sum:
            return None

        credit_card = self.repository.find_one_by_number(number)
        if credit_card is None:
            return None

        if credit_card.pin != pin:
            return None

        return credit_card


class Exit(ActionInterface):
    def __init__(self):
        self.id = 0

    def run(self):
        raise Terminate

    def option(self) -> None:
        print(f'{self.id}. Exit')


class Balance(ActionInterface):
    def __init__(self):
        self.id = 1

    def run(self):
        print('Balance', BankSystem.logged.balance)

    def option(self) -> None:
        print(f'{self.id}. Balance')


class AddIncome(ActionInterface):
    def __init__(self, repository: Repository):
        self.id = 2
        self.repository = repository

    def run(self):
        print('Enter income:')
        income = int(input())
        credit_card = BankSystem.logged
        self.repository.add_income(credit_card, income)
        print('Income was added!')

    def option(self) -> None:
        print(f'{self.id}. Add income')


class DoTransfer(ActionInterface):
    def __init__(self, repository: Repository):
        self.id = 3
        self.repository = repository
        self.algorithm = LuhnAlgorithm()

    def run(self):
        print('Transfer')
        print('Enter card number:')
        number = input()
        if not self.is_valid_card(number):
            print('Probably you make mistake in the card number. Please try again!')
            return

        from_credit_card = BankSystem.logged
        to_credit_card = self.find(number)
        if to_credit_card is None:
            print('Such a card does not exist.')
            return

        print('Enter how much money you want to transfer:')
        money = int(input())
        if money > from_credit_card.balance:
            print('Not enough money!')
            return

        self.repository.transfer_money(from_credit_card, to_credit_card, money)

    def is_valid_card(self, number: str):
        if len(number) != 16:
            return False

        check_sum = number[-1]
        calculated_check_sum = self.algorithm.generate_checksum(number[0:-1])

        if check_sum != calculated_check_sum:
            return False

        return True

    def find(self, number: str):
        credit_card = self.repository.find_one_by_number(number)
        if credit_card is None:
            return None

        return credit_card

    def option(self) -> None:
        print(f'{self.id}. Do transfer')


class CloseAccount(ActionInterface):
    def __init__(self, repository: Repository):
        self.id = 4
        self.repository = repository

    def run(self):
        credit_card = BankSystem.logged
        self.repository.delete(credit_card)
        BankSystem.logged = None

    def option(self) -> None:
        print(f'{self.id}. Close account')


class LogOutAccount(ActionInterface):
    def __init__(self):
        self.id = 5

    def run(self):
        BankSystem.logged = None

    def option(self) -> None:
        print(f'{self.id}. Log out')


class Terminate(Exception):
    pass


class BankSystem:
    logged: CreditCard = None

    def __init__(self):
        self.repository = Repository()
        self.public_actions: list = [
            CreateAccount(self.repository),
            LogIntoAccount(self.repository),
            Exit()
        ]

        self.logged_actions: list = [
            Balance(),
            AddIncome(self.repository),
            DoTransfer(self.repository),
            CloseAccount(self.repository),
            LogOutAccount(),
            Exit()
        ]

    def action(self, option):
        for action in self.get_actions():
            if action.id != option:
                continue

            action.run()

    def get_actions(self):
        if BankSystem.logged:
            return self.logged_actions
        else:
            return self.public_actions

    def menu(self):
        for action in self.get_actions():
            action.option()

    def run(self):
        while True:
            self.menu()
            option = int(input())
            try:
                print()
                self.action(option)
                print()
            except Terminate:
                break


app = BankSystem()
app.run()
