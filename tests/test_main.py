from main import clean_markdown, local_link, slugify


def test_slugify():
    assert slugify("Hello & Setup!") == "hello-and-setup"


def test_local_article_link():
    files = {"123": "123-example.md"}
    value = local_link("/hc/en-us/articles/123-Example#step", files)
    assert value == "./123-example.md#step"


def test_clean_markdown():
    article = {
        "id": 123,
        "title": "Setup",
        "html_url": "https://support.optisigns.com/hc/en-us/articles/123-Setup",
        "body": "<nav>Menu</nav><h2>Start</h2><pre><code>echo ok</code></pre>",
    }
    result = clean_markdown(article, {"123": "123-setup.md"})
    assert "Menu" not in result
    assert "## Start" in result
    assert "echo ok" in result
