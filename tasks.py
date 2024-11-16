import pypub
import concurrent.futures
from utils import get_post_links, add_formatted_text_to_cover
from pypubpatch import *
import uuid, base64

def create_epub(self, params: dict):
    short_uuid = base64.urlsafe_b64encode(uuid.uuid1().bytes).rstrip(b'=').decode('ascii')
    logger = Logger(params, short_uuid)
    try:
        links = get_post_links(params)
        exclude = set(params["exclude"])
        links = list(filter(lambda link: link not in exclude, links))

        if (params["reverse"]):
            links.reverse()
        
        chapters = [None] * len(links)

        epub = pypub.Epub(params["title"])
        epub.creator = "blog-to-epub"
        epub.publisher = "blog-to-epub"

        cover_output_path = "{}_{}.png".format(params["title"], short_uuid)
        add_formatted_text_to_cover("./covers/{}.png".format(params["cover"]), 
                                    params["title"], params["url"], cover_output_path)
        epub.cover = os.path.abspath(cover_output_path)

        update_counter = 0

        def create_chapter_from_url(link):
            try:
                chapter = pypub.create_chapter_from_url(link)
                logger.add_message(LogMessage("success", "retrieval", link))
                return chapter
            except: 
                logger.add_message(LogMessage("fail", "retrieval", link))
                return None
        
        def get_data():
            return {
                "messages": logger.get_messages(), 
                "stats": logger.get_stats()
            }

        def update_state():
            nonlocal update_counter
            update_counter += 1
            if update_counter % 5 == 1:
                self.update_state(state='PROGRESS', meta={
                    'status': 'progress', 
                    'data': get_data()
                })

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(create_chapter_from_url, item): idx for idx, item in enumerate(links)}
            
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                chapters[idx] = future.result()
                update_state()

        for chapter in chapters:
            if chapter:
                epub.add_chapter(chapter)

        epub.builder.link_logger = logger
        epub.builder.update_state = update_state
        edited_title = epub.title.replace(" ", "_")
        file_name = f"{edited_title}_{short_uuid}.epub"
        epub.create(file_name)
        os.remove(file_name)
        os.remove(cover_output_path)

        logger.add_link(public_url)
        logger.save()
        return {'status': 'completed', 'data': get_data(), 'link': public_url}
    
    except Exception as e:
        logger.add_error(str(e))
        logger.save()
        raise e
