#!/bin/bash

## Update cipher.patch
## (made for simplicity - may need to update file paths accordingly)
# recommended to add git hook to apply this before a push to ci/cd

# changes to cipher are being made in cipher.new.py to keep the pip
# installed version untouched and allow for patch creation. the patch
# created here is applied upon docker container creation.
diff -u ~/.local/lib/python3.10/site-packages/pytube/cipher.py cipher.new.py > cipher.patch
