<?php

/* This file is part of Jeedom.
*
* Jeedom is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* Jeedom is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with Jeedom. If not, see <http://www.gnu.org/licenses/>.
*/
require_once dirname(__FILE__) . "/../../../../core/php/core.inc.php";

if (!jeedom::apiAccess(init('apikey'), 'eleroha')) {
	echo 'Clef API non valide, vous n\'etes pas autorisé à effectuer cette action';
	die();
}

if (init('test') != '') {
	echo 'OK';
	die();
}
$result = json_decode(file_get_contents("php://input"), true);
if (!is_array($result)) {
	die();
}
log::add('eleroha','debug','Received data from Deamond');

if(array_key_exists('info', $result)===true){
  log::add('eleroha','debug','value: '.$result['info']['value']);
  log::add('eleroha','debug','channel: '.$result['info']['channel']);
  log::add('eleroha','debug','EqLogic_id: '.$result['info']['EqLogic_id']);
  $eleroha = eleroha::byId($result['info']['EqLogic_id']);
  if (is_object($eleroha)) {
    log::add('eleroha','debug','Obj found, saving');
    $cmd = $eleroha->getCmd(null, $result['info']['channel']);
    switch ($result['info']['value']) {
      case '00':
        $result['info']['value']=__('Aucune information', __FILE__);
        break;
      case '01':
        $result['info']['value']=__('Ouvert', __FILE__);
        break;
      case '02':
        $result['info']['value']=__('Fermé', __FILE__);
        break;
      case '03':
        $result['info']['value']=__('Intermédiaire', __FILE__);
        break;
      case '04':
        $result['info']['value']=__('Ventilation', __FILE__);
        break;
      case '05':
        $result['info']['value']=__('Equipement bloqué', __FILE__);
        break;
      case '06':
        $result['info']['value']=__('Surchauffe', __FILE__);
        break;
      case '07':
        $result['info']['value']=__('Timeout', __FILE__);
        break;
      case '08':
        $result['info']['value']=__('Début ouverture', __FILE__);
        break;
      case '09':
        $result['info']['value']=__('Début fermeture', __FILE__);
        break;
      case '0a':
        $result['info']['value']=__('Ouverture', __FILE__);
        break;
      case '0b':
        $result['info']['value']=__('Fermeture', __FILE__);
        break;
      case '0d':
        $result['info']['value']=__('Position inconnue', __FILE__);
        break;
      case '0e':
        $result['info']['value']=__('Top position stop wich is tilt position', __FILE__);
        break;
      case '0f':
        $result['info']['value']=__('Bottom position stop wich is intermediate position', __FILE__);
        break;
      case '10':
        $result['info']['value']=__('Equipement éteint', __FILE__);
        break;
      case '11':
        $result['info']['value']=__('Equipement allumé', __FILE__);
        break;
      default:
        $result['info']['value']=__('Etat inconnu', __FILE__);
    }
    $cmd->event($result['info']['value']);
    $cmd->save();
  }
}
