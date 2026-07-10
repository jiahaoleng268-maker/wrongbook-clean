from apps.api.app.database import DATABASE_URL, init_db


def main() -> None:
    init_db()
    print(f"Database tables initialized: {DATABASE_URL}")


if __name__ == "__main__":
    main()
