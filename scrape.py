import asyncio
from pyppeteer import launch
from selectolax.parser import HTMLParser
import time
import aiohttp
import sqlite3

baseurl = 'https://www.producthunt.com/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'}
conn = sqlite3.connect('producthunt.db')
cursor = conn.cursor()
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS producthunt(title text, tagline text, description text, reviews int, rating int, link text)''')


async def homepage():
    scraper = await launch()
    page = await scraper.newPage()
    await page.goto('https://www.producthunt.com/topics/artificial-intelligence')

    SCROLL_PAUSE_TIME = 5

    last_height = await page.evaluate('document.body.scrollHeight')

    while True:
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
        await asyncio.sleep(SCROLL_PAUSE_TIME)
        new_height = await page.evaluate('document.body.scrollHeight')
        if new_height == last_height:
            break
        last_height = new_height

    # Get the page content and parse it
    content = await page.content()
    parser = HTMLParser(content)
    urls = []
    for c in parser.css('div.styles_item__W4O__'):
        urls.append(baseurl + c.css('a')[0].attributes['href'])
    await scraper.close()
    return urls


async def main(urls):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
            task = asyncio.ensure_future(fetch(session, url))
            tasks.append(task)
        await asyncio.gather(*tasks)


async def fetch(session, url):
    async with session.get(url, headers=headers) as response:
        await scrape(await response.text())


async def scrape(response):
    try:
        parser = HTMLParser(response)
        title = parser.css_first('h1').text()
        tagline = parser.css_first('div.fontSize-18').text()
        description = parser.css_first(
            '.mb-6.color-lighter-grey.fontSize-16.fontWeight-400.noOfLines-undefined').text()
        reviews = parser.css_first(
            '.color-lighter-grey.fontSize-14.fontWeight-400.noOfLines-undefined.styles_count__8g7_v').text()
        rating = parser.css(
            '.styles_readOnlyStar__eipGF.styles_smallStar__vsA_B')
        link = parser.css_first(
            '.color-lighter-grey.fontSize-14.fontWeight-600.noOfLines-undefined.styles_format__w0VVk.flex.align-center').text()

        cursor.execute('''INSERT INTO producthunt(title, tagline, description, reviews, rating, link) VALUES(?,?,?,?,?,?)''',
                       (title, tagline, description, int(reviews.replace("reviews", "")), len(rating), link))
        conn.commit()
    except Exception as e:
        print(e)


if __name__ == '__main__':
    print('Started scraper..')
    start_time = time.time()
    urls = asyncio.run(homepage())
    asyncio.run(main(urls))
    print(f'Elapsed time: {int(time.time() - start_time)} seconds')
