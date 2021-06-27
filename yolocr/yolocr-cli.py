import click
import yolocr
import subprocess
import sys
import locale

LOCALE, _ = locale.getlocale()
help_strings = {
    'cbh': {        # crop_box_height
        'en': 'Height of the crop_box',
        'fr': 'Hauteur de la CropBox délimitant les sous-titres à OCR.'
    },
    'cbd': {        # crop_box_dimension
        'en': 'Size of the crop_box [width, height]',
        'fr': 'Taille en largeur et hauteur du cadre délimitant l\'OCR'
    },
    'cbha': {       # crop_box_height_alt
        'en': '''Height of the alternative crop_box, double the processing time.
Put -1 to deactivate''',
        'fr': '''Hauteur de la CropBox Alternative, utile pour l'OCR des indications.
Double le temps de traitement. Mettre à -1 pour désactiver.'''
    },
    'ssf': {        # supersampling_factor
        'en': 'Supersampling factor. Put -1 to have it automagically select it',
        'fr': '''Facteur de supersampling (multiplication de la résolution de la vidéo).
Mettre à -1 pour calculer le facteur automatiquement.'''
    },
    'umode': {
        'en': '''Set the upscale mode
\'sinc\' (2 taps, faster), \'znedi3\' (slower), \'waifu2x\' (slowest)''',
        'fr': '''Contrôle la méthode d'Upscale.
'sinc' (2 taps, plus rapide), 'znedi3' (plus lent) ou 'waifu2x' (beaucoup plus lent)'''
    },
    'xpnd': {
        'fr': '''EXPERIMENTAL ! Facteur Expand/Inpand.
La valeur 1 est adaptée pour un Supersampling automatique (1080p).
Calcul typique de la valeur : ExpandRatio="RésolutionFinale"/1080.''',
        'en': '''EXPERIMENTAL. Expand ratio.
1 is adapted for automatic supersampling (1080p)
expand_ratio = "final_resolution/1080"'''
    },
    'tmode': {
        'en': '''Threshold to analyze.
'L' for Luma, 'R' for Red, 'B' for Blue, 'G' for Green. ''',
        'fr': """'L' pour Luma, 'R' pour Rouge, 'B' pour Bleu ou 'G' pour Vert.
Seuil à analyser."""
    },
    'thresh': {
        'en': '''Threshold delimiting the subtitles.
Set it at -1 to search with Vapoursynth Editor''',
        'fr': '''Seuil délimitant les sous-titres.
Mettre à -1 pour chercher le seuil à l\'aide de VapourSynth Editor.'''
    },
    'ithresh': {
        'en': '''Threshold delimiting the subtitles.
This value matches the minimal brightness of the inline''',
        'fr': '''Seuil délimitant les sous-titres.
Cette valeur correspond à la luminosité minimale de l'intérieur (Inline)'''
    },
    'scdt': {
        'fr': '''Un seuil trop bas augmente le nombre de faux positifs,
un seuil trop haut ne permet pas de détecter tous les sous-titres.''',
        'en': '''Setting this threshold too low increases de number of false positives,
too high and it won't detect all of the subtitles.'''
    },
    'othresh': {
        'fr': '''Seuil délimitant les sous-titres.
Cette valeur correspond à la luminosité maximale de l'extérieur (Outline).''',
        'en': '''Threshold delimiting the subtitles.
This value matches the maximale brightness of the outline'''
    }
}


def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


@click.command()
@click.option(
    '--source-file',
    '-f',
    help=help_strings['sf']['fr'] if 'fr' in LOCALE else help_strings['sf']['en']
)
@click.option(
    '--crop_box_dimension',
    '--cbd',
    help=help_strings['cbd']['fr'] if 'fr' in LOCALE else help_strings['cbd']['en']
)
@click.option(
    '--crop_box_height',
    '--cbh',
    help=help_strings['cbh']['fr'] if 'fr' in LOCALE else help_strings['cbh']['en']
)
@click.option(
    '--crop_box_height_alt',
    '--cbha',
    help=help_strings['cbha']['fr'] if 'fr' in LOCALE else help_strings['cbha']['en']
)
@click.option(
    '--lang',
    '-l',
    default='eng',
    help='Language to perform the OCR in'
)
def main(
    source_file: str,
    crop_box_height: int,
    crop_box_dimension: str,
    language: str
):
    """CLI for the yolocr toolkit"""
    try:
        import tqdm, PIL, tesserocr, toml
    except ImportError:
        click.echo('Missing dependencies\nInstalling…')
        for package in ('toml', 'tesserocr', 'PIL', 'toml'):
            install(package)
    proc = subprocess.Popen(
        ['vspipe', 'yolocr/YoloCR.py', '-y', '-'],
        stdout=subprocess.PIPE
    )
    proc = subprocess.Popen(
        [
            'ffmpeg',
            '-i',
            '-',
            '-c:v',
            'mpeg4',
            '-qscale:v',
            '3',
            '-y',
            '-f',
            'm4v',
            'data/filtered.mp4'
        ],
        stdin=proc.stdout
    )
    proc.wait()
    yolocr.main(language, 'data/filtered.mp4')


if __name__ == '__main__':
    main()
