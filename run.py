from app import create_app

app = create_app()

if __name__ == "__main__":
    # Reloader disabled: SQLite does not tolerate two processes on one file
    app.run(debug=True, use_reloader=False)
