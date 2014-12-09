# gist

Command line python tool for listing, downloading and uploading gists.

### Requirements

- requests (Python module)

### Installing without git

```csh
wget https://raw.githubusercontent.com/Adcroft/gist/master/gist.py
```
or
```csh
curl -O https://raw.githubusercontent.com/Adcroft/gist/master/gist.py
```

### Usage

```csh
./gist.py login MY_GITHUB_NAME
./gist.py list
./gist.py get 123456789
./gist.py create -t 'Description goes here' file1.py file2.py
./gist.py update 123456789 file2.py file3.py
```
