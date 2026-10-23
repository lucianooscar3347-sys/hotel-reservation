from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_facture_pdf(facture):
    r, c, h, cur = facture.reservation, facture.reservation.client, settings.HOTEL_INFO, settings.CURRENCY
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=facture.numero_facture)
    st = getSampleStyleSheet()
    money = lambda v: f'{v:,.2f} {cur}'.replace(',', ' ')
    head = ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f3a5f'))
    els = [
        Paragraph(h['name'], st['Title']),
        Paragraph(f"{h['address']}<br/>{h['phone']} — {h['email']}", st['Normal']), Spacer(1, 18),
        Paragraph(f'FACTURE {facture.numero_facture}', st['Heading2']),
        Paragraph(f'Date d\'émission : {facture.date_emission:%d/%m/%Y}<br/>Réservation : {r.numero_reservation}', st['Normal']),
        Spacer(1, 12),
        Paragraph(f'<b>Client :</b> {c.nom_complet}<br/>{c.email} — {c.telephone}', st['Normal']), Spacer(1, 14),
    ]
    t = Table([['Chambre', 'Arrivée', 'Départ', 'Nuits', 'Prix / nuit', 'Total'],
               [r.chambre.numero, f'{r.date_arrivee:%d/%m/%Y}', f'{r.date_depart:%d/%m/%Y}', r.nb_nuits,
                money(r.prix_nuit), money(facture.montant_total)]])
    t.setStyle(TableStyle([head, ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)]))
    els += [t, Spacer(1, 14)]
    paye = facture.montant_paye
    t2 = Table([['Total', money(facture.montant_total)], ['Payé', money(paye)],
                ['Reste à payer', money(max(facture.montant_total - paye, 0))]], colWidths=[120, 140], hAlign='RIGHT')
    t2.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold')]))
    els += [t2, Spacer(1, 24), Paragraph('Merci de votre confiance.', st['Italic'])]
    doc.build(els)
    return buf.getvalue()
