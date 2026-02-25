urutan=$(tail -n 1 README.rst | awk -F "." '{print $1}') || exit 1
urutan=$((urutan + 1)) || exit 1
ref=$(~/env/bin/python web_to_rst_link.py $1) || exit 1
echo $urutan. $ref >> README.rst
tail -n 2 README.rst
