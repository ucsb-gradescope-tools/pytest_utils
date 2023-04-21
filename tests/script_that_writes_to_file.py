import sys


def main(input_file, output_file):
    with open(input_file) as file:
        text = file.read()

    text = ''.join(c.upper() if c in 'aeoiu' else c for c in text)

    with open(output_file, 'w') as file:
        file.write(text)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
