from datetime import date
import sys
import os
import frontmatter


def metadata_is_complete(metadata, filename):
    """Check whether the metadata contains every item we need."""

    #print(filename)

    # don't check blogs before 2019-11-29
    if metadata['date'] < date(2019,11,29):
        return 0

    meta = set(metadata.keys())
    # common = ['title', 'author', 'date', 'summary', 'tags', 'image']
    blog = {'categories', 'title', 'author', 'date', 'summary', 'tags', 'image'}
    case_study = {'customer', 'customerCategory', 'logo', 'title', 'author', 'date', 'summary', 'tags', 'image'}

    # check if metadata keys are complete
    if blog <= meta or case_study <= meta:
        return 0
    else:
        print("\n" + filename + " misses frontmatters. Please check again.\n")
        return 1


def metadata_is_correct(metadata, filename):
    """Check whehter the metadata conforms to our requirements."""
    #print(filename)

    flag = 0

    if ('categories' in metadata.keys()) and (str(metadata['categories'])[2:-2] not in
    ('Product', 'Engineering', 'Community', 'Company')):
        print(filename + " has an unusual category: " + str(metadata['categories']) +
        ". Please verify its correctness. \n")
        flag += 1

    if ('image' in metadata.keys()) and (metadata['image'][:13] != '/images/blog/'):
        print(filename + " has a wrong image path. It should begin with '/images/blog/'.\n")
        flag += 1

    #if len(metadata['title']) > 60:
    #    print(filename + " has a long title (< 60 characters recommended). Are you sure?\n")
    #if len(metadata['summary']) > 300:
    #    print(filename + " has a long summary (< 300 characters recommended). Are you sure?\n")

    return flag


if __name__ == "__main__":

    count = 0

    for filename in sys.argv[1:]:
        mark = 0

        if os.path.isfile(filename) and filename not in ('README.md','pull-request-template.md'):
            #metadata = {}
            #content = {}
            with open(filename) as f:
                metadata, content = frontmatter.parse(f.read())
            if metadata_is_complete(metadata, filename):
                mark += 1
            if metadata_is_correct(metadata, filename):
                mark += 1
            if mark:
                count += 1

    if count:
        print("The above issues will cause website build failure. Please fix them.\n")
        exit(1)
