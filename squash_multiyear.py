import argparse
from xml.dom.expatbuilder import parseString



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--control-file', help="control file")    
    args = parser.parse_args()
    
if __name__ == '__main__':
    main()

