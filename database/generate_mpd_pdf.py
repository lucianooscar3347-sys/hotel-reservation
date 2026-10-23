#!/usr/bin/env python3
"""Génère le PDF du MPD (Modèle Physique des Données) à partir de database/schema.sql.

Usage (depuis la racine du projet) :
    python database/generate_mpd_pdf.py

Résultat : frontend/public/docs/mpd.pdf, affiché par le bouton « À propos » du site.
Pour utiliser votre propre PDF, remplacez simplement ce fichier (même nom) ; ce script est facultatif.
Dépendance : reportlab (déjà dans backend/requirements.txt).
"""
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / 'database' / 'schema.sql'
OUT = ROOT / 'frontend' / 'public' / 'docs' / 'mpd.pdf'

NAVY, NAVY2, GOLD = colors.HexColor('#14284b'), colors.HexColor('#1f3a6b'), colors.HexColor('#c9a24d')
INK, MUTED, LINE = colors.HexColor('#1c2434'), colors.HexColor('#667085'), colors.HexColor('#d3d9e6')
PK_BG, FK_BG, ROW_BG = colors.HexColor('#fbf3dc'), colors.HexColor('#e8effb'), colors.white

# Tables métier affichées (les tables techniques Django : auth_*, django_*, token_blacklist_*, users_groups… sont omises).
TABLES = ['categories_chambres', 'chambres', 'chambre_equipement', 'equipements',
          'users', 'clients', 'reservations', 'reservation_services',
          'factures', 'paiements', 'services']

DESCRIPTIONS = {
    'users': 'Comptes de connexion (rôles ADMIN, RECEPTIONNISTE, CLIENT).',
    'clients': 'Fiche client : identité, coordonnées, numéro de CIN (14 chiffres).',
    'categories_chambres': 'Catégories de chambres (Standard, Suite…).',
    'chambres': 'Chambres de l\'hôtel : prix par nuit (minimum 20 000 Ar), capacité, statut, photo.',
    'equipements': 'Équipements proposés (Wi-Fi, climatisation…).',
    'chambre_equipement': 'Table d\'association N-N entre chambres et équipements.',
    'services': 'Services additionnels facturables (petit-déjeuner, navette…).',
    'reservations': 'Séjours : dates, occupants, montants détaillés, statut. Anti double réservation garanti par la base.',
    'reservation_services': 'Services choisis pour une réservation (nom et prix figés au moment de la réservation).',
    'paiements': 'Paiements enregistrés pour une réservation.',
    'factures': 'Facture émise pour une réservation (une seule par réservation).',
}
REGLES = {
    ('clients', 'numero_piece_identite'): 'Règle applicative : exactement 14 chiffres.',
}


# ---------------------------------------------------------------- lecture du schéma
def parse_schema(sql):
    tables = {}
    for m in re.finditer(r'CREATE TABLE public\.(\w+) \((.*?)\n\);', sql, re.S):
        name, body = m.group(1), m.group(2)
        cols, checks = [], []
        for line in body.strip().split('\n'):
            line = line.strip().rstrip(',')
            if line.startswith('CONSTRAINT'):
                mm = re.match(r'CONSTRAINT (\w+) CHECK \((.*)\)$', line)
                if mm:
                    checks.append((mm.group(1), mm.group(2)))
                continue
            mm = re.match(r'(\w+) (.+)$', line)
            if not mm:
                continue
            typ = re.sub(r' (NOT NULL|DEFAULT).*$', '', mm.group(2))
            typ = (typ.replace('character varying', 'varchar').replace('timestamp with time zone', 'timestamptz')
                   .replace('numeric', 'numeric'))
            cols.append({'name': mm.group(1), 'type': typ, 'notnull': 'NOT NULL' in mm.group(2)})
        tables[name] = {'cols': cols, 'pk': [], 'uq': [], 'fk': {}, 'checks': checks, 'excl': []}
    for m in re.finditer(r'ALTER TABLE ONLY public\.(\w+)\s+ADD CONSTRAINT (\w+) (.+?);', sql, re.S):
        t, cname, rest = m.group(1), m.group(2), ' '.join(m.group(3).split())
        if t not in tables:
            continue
        if rest.startswith('PRIMARY KEY'):
            tables[t]['pk'] = re.findall(r'\((.*?)\)', rest)[0].split(', ')
        elif rest.startswith('UNIQUE'):
            tables[t]['uq'].append(re.findall(r'\((.*?)\)', rest)[0].split(', '))
        elif rest.startswith('FOREIGN KEY'):
            mm = re.match(r'FOREIGN KEY \((\w+)\) REFERENCES public\.(\w+)\((\w+)\)', rest)
            tables[t]['fk'][mm.group(1)] = (mm.group(2), mm.group(3))
        elif rest.startswith('EXCLUDE'):
            tables[t]['excl'].append(cname)
    for m in re.finditer(r'CREATE UNIQUE INDEX \w+ ON public\.(\w+) USING btree \(lower\(\(\((\w+)\)::text\)\)\)', sql):
        if m.group(1) in tables:
            tables[m.group(1)]['uq'].append([f'lower({m.group(2)})'])
    return tables


# ---------------------------------------------------------------- page 1 : diagramme
ROW_H, HEAD_H, BOX_W = 13.2, 21, 216
X = [30, 336, 642, 948]  # colonnes
# (colonne, y du haut) ; y mesuré depuis le haut de la page
POS = {
    'categories_chambres': (0, 112), 'chambres': (1, 112), 'chambre_equipement': (2, 112), 'equipements': (3, 112),
    'users': (0, 330), 'clients': (1, 330), 'reservations': (2, 330), 'reservation_services': (3, 330),
    'factures': (1, 648), 'paiements': (2, 648), 'services': (3, 648),
}
# (enfant, colonne FK, côté de l'enfant par où arrive le lien, voie dans l'espace entre colonnes)
LINKS = [
    ('chambres', 'categorie_id', 'L', 20), ('chambre_equipement', 'chambre_id', 'L', 20),
    ('chambre_equipement', 'equipement_id', 'R', 20), ('clients', 'user_id', 'L', 20),
    ('reservations', 'chambre_id', 'L', 45), ('reservations', 'client_id', 'L', 70),
    ('reservations', 'cree_par_id', 'L', 20), ('reservation_services', 'reservation_id', 'L', 20),
    ('reservation_services', 'service_id', 'V', 0), ('paiements', 'reservation_id', 'V', 0),
    ('factures', 'reservation_id', 'V2', 0),
]


def box_height(t):
    return HEAD_H + ROW_H * len(t['cols']) + 6


def draw_page1(c, doc, tables):
    W, H = landscape(A3)
    c.setFillColor(colors.HexColor('#f6f8fc')); c.rect(0, 0, W, H, stroke=0, fill=1)
    # bandeau titre
    c.setFillColor(NAVY); c.rect(0, H - 82, W, 82, stroke=0, fill=1)
    c.setFillColor(GOLD); c.rect(0, H - 86, W, 4, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont('Helvetica-Bold', 25)
    c.drawString(30, H - 42, 'Modèle Physique des Données (MPD)')
    c.setFont('Helvetica', 11.5); c.setFillColor(colors.HexColor('#c3cde2'))
    c.drawString(30, H - 64, 'Grand Hôtel — Système de réservation  ·  SGBD PostgreSQL  ·  Diagramme des tables métier, clés primaires et clés étrangères')
    c.setFont('Helvetica-Bold', 11); c.setFillColor(GOLD)
    c.drawRightString(W - 30, H - 42, 'Version 2.0')

    geo = {}
    for name, (col, ytop) in POS.items():
        geo[name] = {'x': X[col], 'y': H - ytop, 'h': box_height(tables[name])}  # y = bord haut (repère PDF)

    def row_y(name, colname):
        t = tables[name]
        i = [k['name'] for k in t['cols']].index(colname)
        return geo[name]['y'] - HEAD_H - ROW_H * i - ROW_H / 2

    def label(x, y, txt, anchor='c'):
        c.setFont('Helvetica-Bold', 8)
        w = c.stringWidth(txt, 'Helvetica-Bold', 8) + 5
        c.setFillColor(colors.white); c.setStrokeColor(NAVY2); c.setLineWidth(.6)
        c.roundRect(x - w / 2, y - 5.5, w, 11, 3, stroke=1, fill=1)
        c.setFillColor(NAVY2); c.drawCentredString(x, y - 2.8, txt)

    # liens (dessinés avant les tables : les boîtes passent par-dessus)
    c.setStrokeColor(NAVY2); c.setLineWidth(1.15)
    for child, fk, side, lane in LINKS:
        parent, pcol = tables[child]['fk'][fk]
        unique = [fk] in tables[child]['uq']
        n_lab = '1' if unique else 'N'
        p, ch = geo[parent], geo[child]
        py, cy = row_y(parent, pcol), row_y(child, fk)
        if side == 'V':  # enfant et parent dans la même colonne : trait vertical centré
            xm = ch['x'] + BOX_W / 2
            top_child = ch['y'] > p['y']  # l'enfant est au-dessus du parent
            if top_child:
                a, b = p['y'], ch['y'] - ch['h']
            else:
                a, b = p['y'] - p['h'], ch['y']
            c.line(xm, a, xm, b)
            label(xm, a - (12 if not top_child else -12) * (1 if not top_child else 1), '1')
            label(xm, b + (12 if not top_child else -12), n_lab)
            continue
        if side == 'V2':  # facture : du bas de la réservation vers le haut de la facture
            xs, xe = p['x'] + 62, ch['x'] + BOX_W / 2
            ys, ye = p['y'] - p['h'], ch['y']
            ymid = (ys + ye) / 2 + 6
            c.line(xs, ys, xs, ymid); c.line(xs, ymid, xe, ymid); c.line(xe, ymid, xe, ye)
            label(xs, ys - 12, '1'); label(xe, ye + 12, '1' if unique else 'N')
            continue
        if side == 'L':  # arrive par la gauche de l'enfant (parent à gauche)
            xs, xe = p['x'] + BOX_W, ch['x']
            lane_x = xs + lane
            c.line(xs, py, lane_x, py); c.line(lane_x, py, lane_x, cy); c.line(lane_x, cy, xe, cy)
            label(xs + 11, py + 9, '1'); label(xe - 11, cy + 9, n_lab)
        else:  # 'R' : arrive par la droite de l'enfant (parent à droite)
            xs, xe = p['x'], ch['x'] + BOX_W
            lane_x = xe + lane
            c.line(xs, py, lane_x, py); c.line(lane_x, py, lane_x, cy); c.line(lane_x, cy, xe, cy)
            label(xs - 11, py + 9, '1'); label(xe + 11, cy + 9, n_lab)

    # tables
    for name, g in geo.items():
        t = tables[name]
        x, ytop, h = g['x'], g['y'], g['h']
        c.setFillColor(colors.Color(0, 0, 0, .06)); c.roundRect(x + 2.5, ytop - h - 2.5, BOX_W, h, 6, stroke=0, fill=1)  # ombre
        c.setFillColor(colors.white); c.setStrokeColor(NAVY); c.setLineWidth(1.1)
        c.roundRect(x, ytop - h, BOX_W, h, 6, stroke=1, fill=1)
        c.saveState(); p = c.beginPath(); p.roundRect(x, ytop - h, BOX_W, h, 6); c.clipPath(p, stroke=0, fill=0)
        c.setFillColor(NAVY); c.rect(x, ytop - HEAD_H, BOX_W, HEAD_H, stroke=0, fill=1)
        c.setFillColor(GOLD); c.rect(x, ytop - HEAD_H - 1.2, BOX_W, 1.2, stroke=0, fill=1)
        for i, col in enumerate(t['cols']):
            ry = ytop - HEAD_H - ROW_H * (i + 1)
            is_pk, is_fk = col['name'] in t['pk'], col['name'] in t['fk']
            if is_pk or is_fk:
                c.setFillColor(PK_BG if is_pk else FK_BG); c.rect(x, ry, BOX_W, ROW_H, stroke=0, fill=1)
            c.setStrokeColor(colors.HexColor('#edf0f6')); c.setLineWidth(.4); c.line(x, ry, x + BOX_W, ry)
        c.restoreState()
        c.setFillColor(colors.white); c.setFont('Helvetica-Bold', 10.5); c.drawString(x + 9, ytop - 14.2, name)
        for i, col in enumerate(t['cols']):
            ry = ytop - HEAD_H - ROW_H * (i + 1) + 3.6
            is_pk, is_fk = col['name'] in t['pk'], col['name'] in t['fk']
            is_uq = any(u == [col['name']] for u in t['uq']) and not is_pk
            tag = 'PK' if is_pk else 'FK' if is_fk else 'UQ' if is_uq else ''
            if tag:
                c.setFillColor(GOLD if tag == 'PK' else NAVY2 if tag == 'FK' else MUTED)
                c.roundRect(x + 6, ry - 1.6, 15, 9, 2, stroke=0, fill=1)
                c.setFillColor(colors.white); c.setFont('Helvetica-Bold', 6.2); c.drawCentredString(x + 13.5, ry + .6, tag)
            c.setFillColor(INK); c.setFont('Helvetica-Bold' if is_pk else 'Helvetica', 8.2)
            c.drawString(x + 25, ry, col['name'])
            c.setFillColor(MUTED); c.setFont('Helvetica', 7.4)
            suffix = '' if col['notnull'] else '  null'
            c.drawRightString(x + BOX_W - 7, ry, col['type'] + suffix)

    # légende
    lx, ly = X[0], H - 648
    c.setFillColor(colors.white); c.setStrokeColor(LINE); c.setLineWidth(.8)
    c.roundRect(lx, ly - 150, BOX_W + 70, 150, 8, stroke=1, fill=1)
    c.setFillColor(NAVY); c.setFont('Helvetica-Bold', 10.5); c.drawString(lx + 12, ly - 20, 'Légende')
    items = [('PK', GOLD, 'Clé primaire'), ('FK', NAVY2, 'Clé étrangère (référence une autre table)'),
             ('UQ', MUTED, 'Valeur unique (index UNIQUE)')]
    for i, (tag, col, txt) in enumerate(items):
        yy = ly - 40 - i * 17
        c.setFillColor(col); c.roundRect(lx + 12, yy - 2, 17, 10, 2, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont('Helvetica-Bold', 6.6); c.drawCentredString(lx + 20.5, yy + 1, tag)
        c.setFillColor(INK); c.setFont('Helvetica', 8.6); c.drawString(lx + 38, yy, txt)
    c.setFont('Helvetica', 8.6)
    c.setFillColor(INK); c.drawString(lx + 12, ly - 96, '« null » : la colonne accepte NULL.   « 1 » / « N » : cardinalité du lien.')
    c.drawString(lx + 12, ly - 110, 'Liens : de la clé primaire (côté « 1 ») vers la clé étrangère (côté « N »).')
    c.setFillColor(MUTED); c.setFont('Helvetica-Oblique', 8)
    c.drawString(lx + 12, ly - 128, 'Tables techniques Django (auth_*, django_*, token_blacklist_*) non représentées.')
    c.setFillColor(MUTED); c.setFont('Helvetica', 8)
    c.drawRightString(W - 30, 18, 'Source : database/schema.sql  ·  Régénérer : python database/generate_mpd_pdf.py')


# ---------------------------------------------------------------- pages suivantes : dictionnaire
def build_dictionary(tables):
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=18, leading=24, textColor=NAVY, spaceAfter=4)
    sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5, textColor=MUTED, spaceAfter=12, leading=13)
    h2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, textColor=NAVY, spaceBefore=12, spaceAfter=1)
    desc = ParagraphStyle('desc', fontName='Helvetica-Oblique', fontSize=8.6, textColor=MUTED, spaceAfter=5, leading=11)
    cell = ParagraphStyle('cell', fontName='Helvetica', fontSize=8, textColor=INK, leading=10)
    cellb = ParagraphStyle('cellb', parent=cell, fontName='Helvetica-Bold')
    note = ParagraphStyle('note', parent=cell, fontSize=7.8, textColor=MUTED, leading=10.2)
    story = [Paragraph('Dictionnaire des données', h1),
             Paragraph('Description de chaque table du MPD : colonnes, types PostgreSQL, nullité et contraintes.', sub)]
    for name in TABLES:
        t = tables[name]
        rows = [[Paragraph('<b>Colonne</b>', cell), Paragraph('<b>Type</b>', cell), Paragraph('<b>Null</b>', cell),
                 Paragraph('<b>Clés et contraintes</b>', cell)]]
        for col in t['cols']:
            n = col['name']
            info = []
            if n in t['pk']:
                info.append('<b>PK</b>')
            if n in t['fk']:
                info.append(f"FK vers {t['fk'][n][0]}({t['fk'][n][1]})")
            if [n] in t['uq'] and n not in t['pk']:
                info.append('UNIQUE')
            if (name, n) in REGLES:
                info.append(REGLES[(name, n)])
            rows.append([Paragraph(n, cellb if n in t['pk'] else cell), Paragraph(col['type'], cell),
                         Paragraph('non' if col['notnull'] else 'oui', cell), Paragraph(' · '.join(info), cell)])
        tbl = Table(rows, colWidths=[44 * mm, 36 * mm, 12 * mm, 84 * mm], repeatRows=1)
        style = [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6ebf5')), ('GRID', (0, 0), (-1, -1), .4, LINE),
                 ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2.6),
                 ('BOTTOMPADDING', (0, 0), (-1, -1), 2.6), ('LEFTPADDING', (0, 0), (-1, -1), 5)]
        for i, col in enumerate(t['cols'], start=1):
            if col['name'] in t['pk']:
                style.append(('BACKGROUND', (0, i), (-1, i), PK_BG))
            elif col['name'] in t['fk']:
                style.append(('BACKGROUND', (0, i), (-1, i), FK_BG))
        tbl.setStyle(TableStyle(style))
        block = [Paragraph(name, h2), Paragraph(DESCRIPTIONS.get(name, ''), desc), tbl]
        extra = []
        composite = [u for u in t['uq'] if len(u) > 1]
        if composite:
            extra.append('Unicité composée : ' + ' ; '.join('(' + ', '.join(u) + ')' for u in composite) + '.')
        for u in t['uq']:
            if len(u) == 1 and u[0].startswith('lower('):
                extra.append(f'Unicité insensible à la casse : {u[0]}.')
        for cname, expr in t['checks']:
            if cname.startswith('chk_'):
                extra.append(f'CHECK {cname} : {expr.replace("(", "").replace(")", "").replace("::numeric", "")}.')
        if t['excl']:
            extra.append('EXCLUDE (excl_resa_chevauchement) : une même chambre ne peut pas avoir deux réservations '
                         'EN_ATTENTE ou CONFIRMEE sur des périodes qui se chevauchent (anti double réservation).')
        if extra:
            block.append(Spacer(1, 3)); block.extend(Paragraph('• ' + e, note) for e in extra)
        story.append(KeepTogether(block))
    return story


def main():
    tables = parse_schema(SCHEMA.read_text(encoding='utf-8'))
    missing = [t for t in TABLES if t not in tables]
    if missing:
        raise SystemExit(f'Tables introuvables dans schema.sql : {missing}')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    A3L = landscape(A3)

    def first(c, d):
        draw_page1(c, d, tables)

    def later(c, d):
        c.setFillColor(NAVY); c.rect(0, A4[1] - 14, A4[0], 14, stroke=0, fill=1)
        c.setFillColor(GOLD); c.rect(0, A4[1] - 16.5, A4[0], 2.5, stroke=0, fill=1)
        c.setFillColor(MUTED); c.setFont('Helvetica', 8)
        c.drawString(18 * mm, 10 * mm, 'Grand Hôtel — MPD · Dictionnaire des données')
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f'Page {d.page}')

    doc = BaseDocTemplate(str(OUT), pagesize=A3L, title='MPD — Modèle Physique des Données — Grand Hôtel',
                          author='Grand Hôtel', subject='Modèle physique des données (PostgreSQL)')
    doc.addPageTemplates([
        PageTemplate(id='diagramme', pagesize=A3L, frames=[Frame(0, 0, 20, 20, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=first),
        PageTemplate(id='dico', pagesize=A4, onPage=later,
                     frames=[Frame(18 * mm, 18 * mm, A4[0] - 36 * mm, A4[1] - 40 * mm, id='f')]),
    ])
    story = [Spacer(1, 1), NextPageTemplate('dico'), PageBreak()] + build_dictionary(tables)
    doc.build(story)
    print(f'PDF généré : {OUT} ({OUT.stat().st_size // 1024} Ko)')


if __name__ == '__main__':
    main()
