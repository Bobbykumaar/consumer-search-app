from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

@app.template_filter('pretty_key')
def pretty_key(key):
    """Convert snake_case or underscored column names into a nicer display format."""
    return key.replace('_', ' ').title().replace("Summary", "").replace("Styra", "").strip()

def get_consumer_data(search_type, value):
    conn = sqlite3.connect("consumers.db")
    cursor = conn.cursor()

    try:
        # Map search type to actual DB column
        column = "consumer_number" if search_type == "consumer_number" else "meter_number"
        
        # Debugging info
        print(f"🔍 Searching by: {column} = {value}")

        cursor.execute(f"SELECT * FROM consumers WHERE {column} = ?", (value,))
        row = cursor.fetchone()

        # Also try stripped version if consumer_number has leading zeros
        if not row and search_type == "consumer_number" and value.lstrip("0") != value:
            cleaned = value.lstrip("0")
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
        search_type = request.form.get("search_type", "consumer_number")
        search_value = request.form.get("search_value", "").strip()

        if search_value:
            result = get_consumer_data(search_type, search_value)
            if not result:
                message = f"No data found for {search_type.replace('_', ' ')}: {search_value}"
        else:
            message = "Please enter a valid input."

    return render_template("index.html", result=result, message=message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
