import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk

from ui.app import JobSearchApp


def main():
    root = tk.Tk()
    JobSearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()