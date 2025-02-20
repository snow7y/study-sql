import os


def main() -> int:
    print(f"Hello, {os.environ['USER']}!")
    return 0

if __name__ == "__main__":
    main()
