import sys


def get_number():
    return input('Number:')


if __name__ == '__main__':
    print(f'My args are {sys.argv}')
    num = get_number()
    print(f'The banana is {num}')
    num = get_number()
    print(f'Another number is 234')
