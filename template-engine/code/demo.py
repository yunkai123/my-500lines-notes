'''使用 Templite 生成 html 的一个简单示例
'''

from templite import Templite

def demo():
    templite = Templite('''
        <h1>Hello {{name|upper}}!</h1>
        {% for topic in topics %}
            <p>You are interested in {{topic}}.</p>
        {% endfor %}
        ''',
        {'upper': str.upper},
    )
    html = templite.render({
        'name': "Wyk",
        'topics': ['Python', 'Java', 'Dota'],
    })

    with open('index.html', 'w') as file_object:
        file_object.write(html)

if __name__ == '__main__':
    demo()
