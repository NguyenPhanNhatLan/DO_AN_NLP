import scrapy
import re
import json

from beauty_crawler.items import BeautyCrawlerItem
from urllib.parse import urlencode
from bs4 import BeautifulSoup

class HasakiSpiderSpider(scrapy.Spider):
    name = "hasaki"
    allowed_domains = ["hasaki.vn"]
    
    base_url= 'https://hasaki.vn/mobile/v3/main/products'
    product_base_url ='https://hasaki.vn/mobile/v3/detail/product'
    item = BeautyCrawlerItem()
    category_slugs = [
        "tay-trang-mat-c48",
        "sua-rua-mat-c19",
        "tay-te-bao-chet-da-mat-c35",
        "toner-c1857",
        "chong-nang-da-mat-c11",
        "cham-soc-vung-da-mat-c297",
        "cham-soc-moi-c2059",
        "mat-na-c30",
        "ho-tro-tri-mun-c2005",
        "serum-tinh-chat-c75",
        "xit-khoang-c7",
        "lotion-sua-duong-c2011",
        "kem-duong-dau-duong-c9"
    ]    
    headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        }
    max_pages = 3
    def start_requests(self):
        
        for cate_slug in self.category_slugs:
            params = {
                'cate_path': cate_slug,
                'size': 40,
                'page':0,
                'has_meta_data': 1,
                'is_desktop': 1,
                'form_key': "c422d3923fe94e22193e5556ae1532ae"
            }
            query_string = urlencode(params)
            full_url = f'{self.base_url}?{query_string}'
            
            yield scrapy.Request(url=full_url, headers=self.headers, callback=self.parse, meta={'cate_slug': cate_slug, 'page':1})
        
            
    def parse(self, response):
        try:
            data = json.loads(response.body)
            products = data.get('data', {}).get('products', [])
            
            cate_slug = response.meta.get('cate_slug','')
            page = response.meta.get('page', 1)
            self.logger.info(f'Category: {cate_slug} - Page {page} - Found {len(products)} products')
        
            for product in products:
                if 'combo' not in product.get('name','').lower():
                    meta_info = {
                        'name': product.get('name', ''),
                        'brand': product.get('brand', {}).get('name', ''),
                        'price': product.get('price', 0),
                        'product_id': product.get('id', ''),
                        'category_slug': cate_slug
                    }
                    product_params = {
                        'product_id': product['id'],
                        'is_desktop': 1
                    }
                    
                    query_string = urlencode(product_params)
                    product_url = f"{self.product_base_url}?{query_string}"
                    

                    yield scrapy.Request(url=product_url, 
                                        headers=self.headers,
                                        callback=self.parse_product,
                                        meta = {'meta_info': meta_info})
            if products and page < self.max_pages:
                next_page = page +1
                params = {
                    'cate_path': cate_slug,
                    'size': 40,
                    'page': next_page,
                    'has_meta_data': 1,
                    'is_desktop': 1,
                    'form_key': "c422d3923fe94e22193e5556ae1532ae"
                }
                
                query_string = urlencode(params)
                next_url = f'{self.base_url}?{query_string}'
                
                yield scrapy.Request(
                    url=next_url,
                    headers=self.headers,
                    callback=self.parse,
                    meta={'cate_slug': cate_slug, 'page': next_page}
                )

        except Exception as e:
            self.logger.error(f'Error parsing products: {e}')
            

    def parse_product(self, response: scrapy.Request):
        try:
            data = json.loads(response.body)
            basic_info = response.meta['meta_info']
            
            item = BeautyCrawlerItem()
            blocks = data.get('data', {}).get('blocks', {})
            
            category = ''
            rating = 0
            url = ''
            gallery = []
            ingredient_raw = ''
            usage_tip = ''
            info_dict = {}
            description_raw = ''
            
            
            for block in blocks:
                if 'common_data' in block:
                    category = block['common_data'].get('category_name', '')
                    rating = block['common_data'].get('rating', {}).get('average', 0)
                    url = block['common_data'].get('url', '')
                    gallery = block['common_data'].get('gallery', [])
                    
                if 'ingredient_data' in block:
                    ingredients = block['ingredient_data'].get('info', {}).get('full', '')
                    ingredient_raw = self.clean_html_bs4(ingredients)
                    
                if 'guide_data' in block:
                    guide = block['guide_data'].get('info', {}).get('full', '')
                    usage_tip = self.clean_html_bs4(guide)
                    
                if 'specification_data' in block:
                    infos = block['specification_data'].get('infos', [])
                    info_dict = {info['label']: info.get('value', '') for info in infos}
                    
                if 'description_data' in block:
                    description_full = block['description_data'].get('info', {}).get('full', '')
                    description_raw = self.clean_html_bs4(description_full)
                
        
            item['name'] = basic_info['name']
            item['brand']= basic_info['brand']
            item['price']= basic_info['price']
            item['category'] = category
            item['rating'] = rating
            item['url'] = url
            item['ingredient_raw'] = ingredient_raw
            item['description_raw'] = description_raw
            item['usage_tip'] = usage_tip
            item['volume'] = info_dict.get('Dung Tích', '')
            item['made_from'] = info_dict.get('Nơi sản xuất', '')
            item['skin_type'] = info_dict.get('Loại da', '')
            item['images'] =[img.get("image", "") for img in gallery]
            
            yield item
        
        except Exception as e:
            self.logger.error(f'Error parsing product detail: {e}')
        
    def clean_html_bs4(self,html):
        if not html:
            return ''
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        text = re.sub(r'\xa0',' ', text)
        text = re.sub(r'\n\s*\n+', r'\n\n', text)
        text = re.sub(r'\n', ' ', text)        
        return text.strip()
    

                    
