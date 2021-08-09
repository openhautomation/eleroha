Présentation
============

**Le plugin Eleroha** interface les stores équipés d'un système Elero avec Jeedom.

![eleroha-logo](../images/eleroha_icon.png)

**Prérequis**

>Pour fonctionner, Eleroha nécessite un stick USB Elero afin d'assurer la communication entre Jeedom et vos équipements Elero.

Aussi, vous devez préhalablement :
1. Associer vos stores Elero avec le stick USB comme cela est décrit dans la documentation Elero.
Vous noterez les channels qui correspondent à vos stores. Cette information vous sera demandée lors de la création de vos équipements dans Jeedom.
2. Placer le stick USB dans un port USB libre de votre box Jeedom

Les principales fonctionnalités de Eleroha sont :

**Le pilotage**

>Eleroha vous permet de monter, descendre, stopper, placer en position ventillation vos stores.

**Le monitoring**

>Eleroha vous indique la postion courante de vos stores

**Le widget Eleroha**

![eleroha-widget](../images/eleroha_widget.png)

**Activation et configuration**

>Après avoir activé, le plugin il est indispensable de :
1. Sélectionner port du stick USB Elero.
2. Saisir le port 55030.
3. Vous pouvez également activer la gestion d'une file d'attente.
Cette fonctionnalité met en attente les commandes reçues et les exécute toutes les 15 secondes dans la limite de 10 actions.
La commande de demande d'état (rafraichissement) est exclue de cette file.

N'oubliez pas de sauvegarder.

![eleroha-config](../images/eleroha_config.png)

**Création de votre équipement**

>Après avoir nommé l'équipement, saisissez le numéro du channel qui correspond à votre store.
Les channels sont numérotés de 1 à 15.
Le channel correspond à celui que vous avez associé avec votre store lors de l'étape de configuration du stick USB Elero.

N'oubliez pas de sauvegarder !

![eleroha-equipement](../images/eleroha_equipement.png)

Félicitation, vous avez terminé.

Vous pouvez actualiser manuellement les informations en cliquant sur l'icône située en haut à droite du widget.

**Informations**

Attention :
* le stick Elero ne gère ni buffer ni file d'attente.
* Le stick Elero essaiera toujours de traiter la dernière commande reçue

Pour chaque commandes (commande de demande d'état exclue), le plugin agira de la manière suivante :

1. T0 -> Envoi de la commande (monter, descendre...).
2. T0+10 secondes -> Envoie de la commande de demande d'état.
3. T0+180 secondes -> Envoie de la commande de demande d'état.

Cette séquence est appliquée également lorsque la gestion de la file d'attente est activée dans le plugin.
Dans le cas où la gestion de la file d'attente n'est pas activée, cette séquence sera interrompue si une autre action est envoyée avant 190 secondes.

Les état gérés par le plugin sont :

* 00 : Aucune information
* 01 : Ouvert
* 02 : Fermé
* 03 : Intermédiaire
* 04 : Ventilation
* 05 : Equipement bloqué
* 06 : Surchauffe
* 07 : Timeout
* 08 : Début ouverture
* 09 : Début fermeture
* 0A : Ouverture
* 0B : Fermeture
* 0C : Arrêté position indéfinie
* 0D : Top position stop wich is tilt position
* 0E : Bottom position stop wich is intermediate position
* 0F : Equipement éteint
* 10 : Equipement allumé
* 11 : Etat inconnu
