import setuptools

setuptools.setup(
    name='visual swebench',
    keywords='nlp, benchmark, code',
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=[
        'beautifulsoup4',
        'chardet',
        'datasets',
        'docker',
        'ghapi',
        'GitPython',
        'pre-commit',
        'python-dotenv',
        'requests',
        'rich',
        'unidiff',
        'tqdm',
        'openai',
    ],
    extras_require={
        'inference': [
            'tiktoken',
            'anthropic',
            'transformers',
            'peft',
            'sentencepiece',
            'protobuf',
            'torch',
            'flash_attn',
            'triton',
            'jedi',
            'tenacity',
        ],
    },
    include_package_data=True,
)