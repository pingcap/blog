import re
import sys
import os

def check_front_matter(filename):

    frontMatter = []
    common = ['title', 'author', 'date', 'summary', 'tags', 'image']
    blog = ['categories']
    caseStudy = ['customer', 'customerCategory', 'logo']
    # optional = ['press_release']
    missing = []

    flag = 0
    type = 0


    with open(filename,'r') as file:

        dashes = 0
        word = ''

        for line in file:
            if re.match(r'(-){3}', line) and dashes == 0: #front matter begins
                dashes = 1
            elif re.match(r'(-){3}', line) and dashes == 1: #front matter ends
                break
            else:
                word = line[:line.find(':')]
                frontMatter.append(word)

        for item in common:
            if item in frontMatter:
                continue
            else:
                flag += 1
                missing.append(item)

        if 'customer' in frontMatter or 'customerCategory' in frontMatter or 'logo' in frontMatter:
            type = 1
            for item in caseStudy:
                if item in frontMatter:
                    continue
                else:
                    flag += 1
                    missing.append(item)
        elif 'categories' in frontMatter:
            type = 2
            for item in blog:
                if item in frontMatter:
                    continue
                else:
                    flag += 1
                    missing.append(item)
        else:
            flag += 1

    if flag:
        if type == 1:
            print("\n" + filename + " is a case study, and it misses the following frontmatters:\n")
        elif type == 2:
            print("\n" + filename + " is a blog, and it misses the following frontmatters:\n")
        else:
            print("\n" + filename + " is neither blog nor case study. Please make sure you add 'categories' or 'customer'.")
            if flag > 1:
                print("In addtion, it misses the following frontmatters:\n")
        print(missing)
        return 1


if __name__ == "__main__":

    count = 0

    for filename in sys.argv[1:]:
        if os.path.isfile(filename):
            mark = check_front_matter(filename)
            if mark:
                count+=1

    if count:
        print("\nThe above issues will cause website build failure. Please fix them.")
        exit(1)
