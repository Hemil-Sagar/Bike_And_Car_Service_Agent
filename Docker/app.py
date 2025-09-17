from flask import Flask, request, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Multiplication Table</title>
</head>
<body>
    <h1>Multiplication Table Generator</h1>
    <form method="POST">
        <input type="text" name="num" placeholder="Enter a number" required>
        <button type="submit">Show Table</button>
    </form>

    {% if table %}
        <h2>Multiplication Table of {{ num }}:</h2>
        <table border="1" cellpadding="5" cellspacing="0">
            {% for i in range(1, 11) %}
                <tr>
                    <td>{{ num }} × {{ i }}</td>
                    <td>{{ num * i }}</td>
                </tr>
            {% endfor %}
        </table>
    {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def table():
    table = False
    num = None
    if request.method == 'POST':
        try:
            num = int(request.form['num'])
            table = True
        except ValueError:
            table = False
            num = "Invalid input! Please enter a number."
    return render_template_string(HTML, table=table, num=num)

if __name__ == '__main__':
    app.run(host="0.0.0.0",port=8000,debug=True)
