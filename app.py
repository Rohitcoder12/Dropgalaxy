from flask import Flask, render_template, request, redirect, url_for, flash
from downloader import get_dropgalaxy_link

app = Flask(__name__)
# A secret key is needed for flashing messages
app.secret_key = 'some_random_secret_string_for_production'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the URL from the form submission
        dropgalaxy_url = request.form.get('url')
        if not dropgalaxy_url:
            flash("Please enter a URL.")
            return redirect(url_for('index'))

        print(f"Processing URL: {dropgalaxy_url}")
        # Call the refactored function
        final_link, error = get_dropgalaxy_link(dropgalaxy_url)

        if error:
            # If there was an error, show it to the user
            print(f"Error: {error}")
            flash(error)
            return redirect(url_for('index'))
        
        if final_link:
            # If successful, redirect the user's browser to the download
            print(f"Success! Redirecting to: {final_link}")
            return redirect(final_link)

    # For a GET request, just show the page
    return render_template('index.html')

if __name__ == '__main__':
    # This is for local testing, not for production on Render
    app.run(debug=True)