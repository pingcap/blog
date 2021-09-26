import sys, os

def check_less_than_symbols(filename):

    lineNum = 0
    flag = 0

    with open(filename,'r') as file:
        for line in file:
            lineNum += 1
            if line.find('&lt;') != -1:
                print("Warning: " + filename + " L" + str(lineNum) + " has a suspicious &lt; mark.")
                flag += 1

    return flag

if __name__ == "__main__":

    count = 0

    for filename in sys.argv[1:]:
        if os.path.isfile(filename):
            mark = check_less_than_symbols(filename)
            if mark:
                print("====================\n")
                count+=1

    if count:
        print("Please take a closer look at the above files. They may have incorrectly converted '<' to '&lt;'. \n")
        exit(1)
