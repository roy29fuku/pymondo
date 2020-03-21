import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

with open("requirements.txt") as f:
    required = f.read().splitlines()

setuptools.setup(
    name='pymondo',
    version='0.0.9',
    author='Ryota Yamada',
    author_email='roy29fuku@gmail.com',
    description='python wrapper for mondo',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/roy29fuku/pymondo',
    packages=setuptools.find_packages(exclude="tests"),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
    ],
    install_requires=required,
    python_requires='>=3.8',
)
