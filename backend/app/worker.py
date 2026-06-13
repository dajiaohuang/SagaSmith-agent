import time


def main():
    print("DND worker ready. Import and summary jobs are exposed through the API.")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()

