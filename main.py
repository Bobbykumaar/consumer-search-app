from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

@app.template_filter('pretty_key')
def pretty_key(key):
    """Convert snake_case or underscored column names into a nicer display format."""
    return key.replace('_', ' ').title().replace("Summary", "").replace("Styra", "").strip()

def get_consumer_data(consumer_number):
    conn = sqlite3.connect("consumers.db")
    cursor = conn.cursor()

    # Debug: Print columns in table
    cursor.execute("PRAGMA table_info(consumers)")
    columns = [col[1] for col in cursor.fetchall()]
    print("🧾 Columns in table:", columns)

    try:
        # Try original input
        cursor.execute("SELECT * FROM consumers WHERE consumer_number = ?", (consumer_number,))
        row = cursor.fetchone()

        # If not found, try without leading zeros
        if not row and consumer_number.lstrip("0") != consumer_number:
            cleaned = consumer_number.lstrip("0")
            cursor.execute("SELECT * FROM consumers WHERE consumer_number = ?", (cleaned,))
            row = cursor.fetchone()

        col_names = [desc[0] for desc in cursor.description] if row else []
        conn.close()

        if row:
            return dict(zip(col_names, row))
        return None
    except Exception as e:
        print("❌ Query error:", e)
        conn.close()
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    message = None
    if request.method == "POST":
        consumer_number = request.form.get("consumer_number", "").strip()
        if consumer_number:
            result = get_consumer_data(consumer_number)
            if not result:
                message = f"No data found for consumer number: {consumer_number}"
        else:
            message = "Please enter a consumer number."
    return render_template("index.html", result=result, message=message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
