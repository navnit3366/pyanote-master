#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pyanote.modificateurs

(C) Lisa Baget et Matthieu Durand, 2018-2019

Ce module contient les fonctions permettant de modifier les actions d'un controleur.
"""
import pyanote.son as son
import pyanote.karaoke as karaoke
import math

MODIFICATEURS_STANDARD = {
    'midi' : False,
    'horloge' : False,
    'defilement': False,
    'kar': False,
    'clavier': False
}

def initialiser_modificateurs(controleur):
    controleur.update(MODIFICATEURS_STANDARD)
    initialiser_notes_actives(controleur) # besoin que quand midi mais compliqué
    controleur['mod_temps'], controleur['mod_temps/chanson'] = 0, {}
    controleur['mod_ticks'], controleur['mod_ticks/chanson'] = 0, {}
    controleur['mod_canaux_libres'], controleur['mod_canaux_libres/chanson'] = [True] * 16, {}
    controleur['mod_kar'] = controleur['fichier'][-4:] == '.kar' ## vrai quand le fichier est de la forme "test.kar"
    controleur['mod_paroles'], controleur['mod_paroles/chanson'] = {0: []}, {}

def preparer_modificateurs(controleur, **params):
    cles_autorisees = list(MODIFICATEURS_STANDARD)
    for cle in params:
        if cle in cles_autorisees:
            controleur[cle] = params[cle]
        else:
            raise TypeError("Parametre inconnu pour les modificateurs.")
    if controleur['midi']:
        initialiser_notes_actives(controleur) # besoin que quand midi mais compliqué
    if controleur['horloge'] or controleur['defilement']:
        controleur['mod_derniere_seconde'] = 0


def reinitialiser_modificateurs(controleur):
    pass

def executer_modificateurs_arret(controleur):
    ''' Cette fonction est exécutée à l'arrêt de la boucle de lecture.
    '''
    if controleur['midi']:
        vider_notes_actives(controleur)

def executer_modificateurs_pause(controleur):
    ''' Cette fonction est exécutée à la pause de la boucle de lecture.
    '''
    if controleur['midi']:
        vider_notes_actives(controleur)

def executer_modificateurs_fin_chanson(controleur):
    ''' Cette fonction est appelée par la boucle de lecture à la fin de chaque chanson.
    '''
    numero_chanson = controleur['index_chanson']
    controleur['mod_temps/chanson'][numero_chanson] = controleur['mod_temps']
    controleur['mod_ticks/chanson'][numero_chanson] = controleur['mod_ticks']
    controleur['mod_temps'] = 0
    controleur['mod_ticks'] = 0
    controleur['mod_canaux_libres/chanson'][numero_chanson] = controleur['mod_canaux_libres']
    controleur['mod_canaux_libres'] = [True] * 16
    if controleur['mod_kar']:
        controleur['mod_paroles/chanson'][numero_chanson] = controleur['mod_paroles']
    if controleur['kar']:
        karaoke.mettre_a_jour_karaoke(controleur['kar'], controleur['mod_paroles'])
    controleur['mod_paroles'] = {0: []}


def executer_modificateurs_fin_album(controleur):
    ''' Cette fonction est appelée par la boucle de lecture à la fin de la dernière chanson d'un album.
    '''
    pass

def executer_modificateurs_delta_temps(controleur, ticks, micros):
    ''' Cette fonction est appelée avant chaque appel de time.sleep pour une durée
        normale (pas modifiée par la vitesse) valant ticks ou micros (suivant unité mesure).
    '''
    controleur['mod_temps'] = controleur['mod_temps'] + micros
    controleur['mod_ticks'] = controleur['mod_ticks'] + ticks
    if controleur['horloge'] or controleur['defilement']:
        nouveau_secondes = math.floor(controleur['mod_temps'] // 10**6)
        if nouveau_secondes > controleur['mod_derniere_seconde']:
            controleur['mod_derniere_seconde'] = nouveau_secondes
            if controleur['horloge']:
                chaine = '{:02}:{:02}'.format(nouveau_secondes // 60, nouveau_secondes % 60)
                #controleur['horloge'].configure(text = chaine)
                controleur['horloge'].set(chaine)
                
            if controleur['defilement']:
                controleur['defilement'].set(nouveau_secondes)

def executer_modificateurs_message_controle(controleur, num_piste, message):
    ''' Cette fonction est appelée à chaque fois que la boucle de lecture doit traiter
    un message de controle sur une certaine piste.
    '''
    if controleur['clavier']:
        gerer_clavier(controleur['clavier'], message)
    if controleur['vitesse'] == float('inf'):
        gerer_canaux_libres(controleur, message)
    elif  controleur['midi']:
        gerer_notes_actives(controleur, num_piste, message)
        son.message_controle(controleur['midi'], message)


def executer_modificateurs_message_meta(controleur, num_piste, message):
    ''' Cette fonction est appelée à chaque fois que la boucle de lecture doit traiter
    un message meta sur une certaine piste.
    '''
    if message[0] == 1 and controleur['mod_kar']: 
        if controleur['vitesse'] == float('inf'): # on est en mode analyse
            ticks = controleur['mod_ticks']
            if ticks == 0:
                controleur['mod_paroles'][0].append(message[1]) ## sauvegarde d'1 titre
            else:
                controleur['mod_paroles'][ticks] = message[1]
        else:
            if controleur['kar']:
                karaoke.changer_couleur_karaoke(controleur['kar'], controleur['mod_ticks'])

def executer_modificateurs_message_systeme(controleur, num_piste, message):
    ''' Cette fonction est appelée à chaque fois que la boucle de lecture doit traiter
    un message système sur une certaine piste.
    '''
    if controleur['midi'] and controleur['vitesse'] < float('inf'):
        son.message_systeme(controleur['midi'], message)

##### FONCTIONS DE GESTION DES NOTES ACTIVES

def initialiser_notes_actives(controleur):
    controleur['mod_notes_actives'] = []
    for i in range(16): # pour chaque canal
        controleur['mod_notes_actives'].append(set([])) ## on utilise ensembles pour enlever et tester appartenance rapidement

def gerer_notes_actives(controleur, num_piste, message):
    instruction = message[0] // 16
    canal = message[0] % 16
    if canal != 9: # pas besoin pour le canal où on n'arrete pas les notes
        if instruction == 9: # c'est un note on mais pas une batterie. Pas de faux note off car corrigé dans pistes.py
            controleur['mod_notes_actives'][canal].add(message[1]) ## on active la note sur le canal
        elif instruction == 8: # c'est un note off
            controleur['mod_notes_actives'][canal].discard(message[1]) ## on desactive

def vider_notes_actives(controleur):
    for canal in range(16):
        for note in controleur['mod_notes_actives'][canal]:
            arreter_note(controleur, note, canal)
        controleur['mod_notes_actives'][canal] = set([]) ## vider l'ensemble

def gerer_canaux_libres(controleur, message):
    if message[0] // 16 == 9: # si c'est un note on
        canal = message[0] % 16
        if canal != 9: # le canal drums est toujours libre
            controleur['mod_canaux_libres'][canal] = False

def arreter_note(controleur, note, canal):
    son.message_controle(controleur['midi'], [0x80 + canal, note, 0])

def gerer_clavier(clavier, message):
    instruction = message[0] // 16
    canal = message[0] % 16
    note = message[1]
    try:
        if instruction == 9 and canal != 9:
            illuminer_touche(clavier.touches[note])
        elif instruction == 8 and canal != 9:
            retablir_touche(clavier.touches[note])
    except KeyError: #Quand ca n'est pas une touche du clavier
        pass

def illuminer_touche(touche):
    touche.configure(bg = touche.altcouleur)
    touche.itemconfigure(touche.texte, state = "disabled")

def retablir_touche(touche):
    touche.configure(bg = touche.couleur)
    touche.itemconfigure(touche.texte, state = "hidden")

