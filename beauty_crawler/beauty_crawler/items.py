# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class BeautyCrawlerItem(scrapy.Item):
    # define the fields for your item here like:
    category = scrapy.Field()
    name = scrapy.Field()
    brand = scrapy.Field()
    price = scrapy.Field()
    ingredient_raw = scrapy.Field()
    usage_tip = scrapy.Field()
    rating = scrapy.Field()
    volume = scrapy.Field()
    skin_type = scrapy.Field()
    description_raw = scrapy.Field()
    made_from = scrapy.Field()
    images = scrapy.Field()
    url = scrapy.Field()
    

