from flask import Flask, render_template, request, send_file
import sqlite3
import io
import csv

app = Flask(__name__)
visit_counter = 0  # simple in-memory visit counter

@app.template_filter('pretty_key')
def pretty_key(key):
    return key.replace('_', ' ').title().replace("Summary", "").replace("Styra", "").strip()

def get_consumer_data(query_value, search_type):
    conn = sqlite3.connect("consumers.db")
    cursor = conn.cursor()

    try:
        column = "consumer_number" if search_type == "consumer" else "New_Meter_QR_Code"

        cursor.execute("PRAGMA table_info(consumers)")
        cursor.execute(f"SELECT * FROM consumers WHERE `{column}` = ?", (query_value,))
        row = cursor.fetchone()

        if not row and query_value.lstrip("0") != query_value:
            cleaned = query_value.lstrip("0")
            cursor.execute(f"SELECT * FROM consumers WHERE `{column}` = ?", (cleaned,))
            row = cursor.fetchone()

        col_names = [desc[0] for desc in cursor.description] if row else []
        conn.close()

        return dict(zip(col_names, row)) if row else None
    except Exception as e:
        print("❌ Query error:", e)
        conn.close()
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    global visit_counter
    visit_counter += 1

    result = None
    message = None
    selected_option = "consumer"

    if request.method == "POST":
        selected_option = request.form.get("search_type", "consumer")
        input_value = request.form.get("input_value", "").strip()

        if input_value:
            result = get_consumer_data(input_value, selected_option)
            if not result:
                message = f"No data found for {selected_option} number: {input_value}"
        else:
            message = "Please enter a value."

    return render_template("index.html", result=result, message=message, selected=selected_option, visits=visit_counter)

@app.route("/download", methods=["POST"])
def download_csv():
    result = request.form.get("csv_data")
    if not result:
        return "No data", 400

    data = eval(result)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(data.keys())
    writer.writerow(data.values())
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='consumer_data.csv'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
