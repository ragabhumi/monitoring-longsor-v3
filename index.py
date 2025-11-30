# -*- coding: utf-8 -*-
"""
Created on Tue Mar 16 15:09:01 2021

@author: yosis
"""

from app import app, server  # server diekspos untuk gunicorn
from layouts import build_layout  # fungsi penyusun layout
import callbacks  # mendaftarkan semua callback

# set layout
app.layout = build_layout()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
