from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello Edu Boost Up!'

@app.route('/test')
def test():
    return 'Test page is working!'

if __name__ == '__main__':
    print('🚀 Testing Flask installation...')
    app.run(debug=True, port=5000)
