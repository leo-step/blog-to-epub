import html
import os
import pypub
import pyxml
from pypub.builder import jinja_env, copy_static, epub_dirs, copy_file, generate_cover
from pypub.factory import REPLACE, SUPPORTED_TAGS, HtmlElement, cast
import urllib.parse
from lxml import etree
from schemas import LogMessage

def is_valid_xml(xml_string):
    try:
        # Parse the XML string
        etree.fromstring(xml_string)
        return True
    except etree.XMLSyntaxError:
        return False

def begin(self):
    """begin building operations w/ basic file structure"""
    # read jinja2 chapter template
    if not self.template:
        self.template = jinja_env.get_template('page.xhtml.j2')
    if self.dirs:
        return self.dirs
    args = (self.epub.title, self.epub.creator)
    self.logger.info('generating: %r (by: %s)' % args)
    # generate base directories and copy static files
    self.dirs = epub_dirs(self.epub.epub_dir)
    copy_static('mimetype', self.dirs.basedir)
    copy_static('container.xml', self.dirs.metainf)
    copy_static('css/coverpage.css', self.dirs.styles)
    copy_static('css/styles.css', self.dirs.styles)
    for path in self.epub.css_paths:
        copy_file(path, self.dirs.styles)
    # generate cover-image
    if self.epub.cover is not None:
        self.cover = os.path.basename(self.epub.cover)
        copy_file(self.epub.cover, self.dirs.images)
    else:
        self.logger.info('generating cover-image (%r by %r)' % args)
        self.cover = generate_cover(*args, self.dirs.images)
    # render cover-image
    fpath    = os.path.join(self.dirs.oebps, 'coverpage.xhtml')
    template = jinja_env.get_template('coverpage.xhtml.j2')
    cover    = os.path.join('images', self.cover)
    with open(fpath, 'w', encoding=self.encoding) as f:
        cover = template.render(cover=cover, epub=self.epub)
        f.write(cover)
    return self.dirs


def render_chapter(self, assign, chapter):
    """render an assigned chapter into the ebook"""
    if not self.dirs or not self.template:
        raise RuntimeError('cannot render_chapter before `begin`')
    # log chapter generation
    chapter.title = chapter.title.split("|")[0].strip()
    self.logger.info('rendering chapter #%d: %r' % (
        assign.play_order, chapter.title))
    # render chapter w/ appropriate kwargs
    args    = (self.logger, chapter, self.dirs.images, self.template)
    kwargs  = {'epub': self.epub, 'chapter': chapter}
    fpath   = os.path.join(self.dirs.oebps, assign.link)
    content = self.factory.render(*args, kwargs, 
        extern_links=self.epub.extern_links)
    with open(fpath, 'wb') as f:
        string_content = content.decode("utf-8")
        clean_content = html.unescape(html.unescape(string_content)).replace('&', '&amp;')
        content_encoded = clean_content.encode("utf-8")
        if is_valid_xml(content_encoded):
            self.chapters.append((assign, chapter))
            f.write(content_encoded)
            self.link_logger.add_message(LogMessage("success", "render", chapter.url))
            self.update_state()
        else:
            self.link_logger.add_message(LogMessage("fail", "render", chapter.url))
            self.update_state()


def cleanup_html(self, content: bytes):
    """
    cleanup html content to only include supported tags
    """
    content = content.decode('utf-8', 'replace').translate(REPLACE).encode()
    # check if we can minimalize the scope
    etree_original   = pyxml.html.fromstring(content)
    etree = etree_original
    body    = etree_original.xpath('.//body')
    etree   = body[0] if body else etree
    content = etree_original.xpath('//*[@class = "content"]')
    etree   = content[0] if content else etree
    article = etree_original.xpath('.//article')
    etree   = article[0] if article else etree
    post_content = etree_original.xpath('//*[contains(@class, "content")][contains(@class, "post")]')
    etree   = post_content[0] if post_content else etree
    article_body = etree_original.xpath('//*[contains(@itemprop, "articleBody")]')
    etree   = article_body[0] if article_body else etree
    # iterate elements in tree and delete/modify them
    for elem in [elem for elem in etree.iter()][1:]:
        # if element tag is supported
        if elem.tag in SUPPORTED_TAGS:
            # remove attributes not approved for specific tag or no value
            for attr, value in list(elem.attrib.items()):
                if attr not in SUPPORTED_TAGS[elem.tag] or not value:
                    elem.attrib.pop(attr)
                elif attr == 'href':
                    elem.attrib['href'] = urllib.parse.quote(elem.attrib['href'])
        # if element is not supported, append children to parent
        else:
            # retrieve parent
            parent = cast(HtmlElement, elem.getparent())
            for child in elem.getchildren():
                parent.append(child)
            parent.remove(elem)
            #NOTE: this is a bug with lxml, some children have
            # text in the parent included in the tail rather
            # than text attribute, so we also append tail to text
            if elem.tail and elem.tail.strip():
                parent.text = (parent.text or '') + elem.tail.strip()
    # fix and remove invalid images
    for img in etree.xpath('.//img'):
        # ensure all images with no src are removed
        if 'src' not in img.attrib:
            cast(HtmlElement, img.getparent()).remove(img)
        # ensure they also have an alt
        elif 'alt' not in img.attrib:
            img.attrib['alt'] = img.attrib['src']
    # return new element-tree
    return etree


pypub.EpubBuilder.begin = begin
pypub.EpubBuilder.render_chapter = render_chapter
pypub.factory.SimpleChapterFactory.cleanup_html = cleanup_html
