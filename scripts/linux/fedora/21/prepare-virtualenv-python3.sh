sudo dnf install -y python3-devel
rm -rf ~/.virtualenvs/crosscompute-python3
virtualenv ~/.virtualenvs/crosscompute-python3 -p /bin/python3
source ~/.virtualenvs/crosscompute-python3/bin/activate
