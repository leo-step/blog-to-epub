import re
from collections import defaultdict
import json
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
from pil_autowrap import fit_text

class Node:
    def __init__(self, root):
        self.root = root
        self.link = root.attrs.get('href')
        self.hash = None
        self.children = []
        self.subtree_size = 1

    def add_child(self, child):
        self.children.append(child)
        self.subtree_size += child.subtree_size

    def set_hash_and_link(self):
        name, attrs = self.root.name, self.root.attrs
        attrs["href"] = ""
        attrs["class"] = []
        child_hashes = list(map(lambda x: x.hash, self.children))
        child_links = set(map(lambda x: x.link, self.children))
        if len(child_links) == 1:
            self.link = list(child_links)[0]
        self.hash = hash(json.dumps([name, attrs, child_hashes], sort_keys=True))
    
    def __str__(self):
        return "{}: {}: {}".format(self.root.name, self.hash, self.link)

def get_request_headers():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " 
        + "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }
    return headers

def is_image_url(url):
    image_extensions = re.compile(r'\.(jpg|jpeg|png|gif|bmp|tiff|webp|svg)$', re.IGNORECASE)
    return bool(image_extensions.search(url))

def get_post_links(params):
    soup = BeautifulSoup(requests.get(params["url"], 
            headers=get_request_headers()).text, features="html.parser")

    node_registry = defaultdict(list)
    subtree_sizes = defaultdict(int)

    def register_node(node: Node):
        if not node.link:
            return
        node_registry[str(node.hash)].append(node)
        subtree_sizes[str(node.hash)] += node.subtree_size

    def dfs(root):
        if not root or not root.name:
            return None
        node = Node(root)
        children = [child for child in root.children if child != '\n']
        for child in children:
            child_node = dfs(child)
            if child_node:
                node.add_child(child_node)
        node.set_hash_and_link()
        register_node(node)
        return node
    
    dfs(soup.body)

    subtree_size_tuples = []
    for key, count in subtree_sizes.items():
        subtree_size_tuples.append((count, key))

    if not subtree_size_tuples:
        return []

    subtree_size_tuples.sort(reverse=True)
    largest_repeating_tree_hash = subtree_size_tuples[0][1]
    nodes = node_registry[largest_repeating_tree_hash]
    
    links_set = set()
    links = []
    for node in nodes:
        if node.link in links_set or is_image_url(node.link):
            continue
        links.append(urljoin(params["url"], node.link))
        links_set.add(node.link)

    return links
    
def depipe(text):
    return text.split("|")[0].strip()

def fetch_title(url: str) -> str:
    """Fetch the title of a webpage given its URL."""
    try:
        response = requests.get(url, timeout=5)  # Set a timeout for the request
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')
        return depipe(title_tag.string) if title_tag else 'No title found'
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return 'Error fetching title'

def get_titles_from_links(links):
    """Fetch titles from a list of links concurrently."""
    titles = []
    with ThreadPoolExecutor() as executor:
        results = executor.map(fetch_title, links)
        titles = list(results)
    return titles

def add_formatted_text_to_cover(image_path, title, url, output_path):
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    color = "#130D0B"
    title_position = (56, 122)
    url_position = (56, 260)

    font = ImageFont.truetype("fonts/OpenSans-Regular.ttf", size=100)
    title_font, wrapped_title_text = fit_text(font, title, 284, 120, max_iterations=10)
    url_font, wrapped_url_text = fit_text(font, url, 284, 14, max_iterations=10)
    
    draw.text(title_position, wrapped_title_text, font=title_font, fill=color)
    draw.text(url_position, wrapped_url_text, font=url_font, fill=color)
    
    img.save(output_path)
