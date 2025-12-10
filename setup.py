from setuptools import setup, find_packages

setup(
    name="enem-extractor",
    version="1.0.2",
    description="Ferramenta para baixar provas e gabaritos do ENEM diretamente do INEP.",
    author="D3-4D",
    license="Apache-2.0",
    packages=find_packages(),
    py_modules=["enemd"],
    install_requires=[
        "requests",
        "beautifulsoup4"
    ],
    extras_require={
        "progress": ["tqdm"],
        "colors": ["colorama"],
        "all": ["tqdm", "colorama"],
    },
    entry_points={
        "console_scripts": [
           "enemd=enemd.main:Download",
        ]
    },
    python_requires=">=3.10",
)
