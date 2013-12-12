#!/usr/bin/env python

"""Process Burmese Majjhima Nikāya."""

from lib import *

division = 'မဇ္ဈိမနိကာယ်'

def mn_sections(html):
    doc = soup(html)
    sections = []
    section = None
    for el in doc.body:
        if el.name == 'h4':
            text = clean(el.text)
            if text[0] == '-':
                text = text[1:]
            if numbers_re.match(text[0]):
                if section:
                    sections.append(section)
                section = {
                    'title': clean(el.text),
                    'content': '',
                }
            elif section:
                section['content'] += tagit('h2', el.text)
        elif section and el.name == 'p':
            section['content'] += tagit('p', el.text)
    if section:
        sections.append(section)
    return sections

if __name__ == '__main__':
    makedirs()
    for input_path in pass3_dir.glob('mn*.html'):
        with input_path.open('r', encoding='utf-8') as input:
            sections = mn_sections(input.read())
        nums = input_path.name.replace('mn', '').replace('.html', '')
        first, last = map(int, nums.split('-'))
        assert len(sections) == last + 1 - first

        for i in range(first, last + 1):
            section = sections[i - first]
            output_path = output_mn_dir / 'mn{}.html'.format(i)
            print('Process: {} to {}'.format(input_path, output_path))
            with output_path.open('w', encoding='utf-8') as output:
                html = output_template.format(division=division,
                    title=section['title'], content=section['content'])
                output.write(html)
