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
try {
    require_once dirname(__FILE__) . "/../../../../core/php/core.inc.php";

    if (!jeedom::apiAccess(init('apikey'), 'eleroha')) {
        echo __('Vous n\'etes pas autorisé à effectuer cette action', __FILE__);
        die();
    }

    if (isset($_GET['test'])) {
    	echo 'OK';
      log::add('eleroha', 'debug', 'Test deamon callback OK');
      die();
    }

    log::add('eleroha','debug','Received data from deamond');

    $result = json_decode(file_get_contents("php://input"), true);
    if($result===false){
      log::add('eleroha','debug','json decode failed');
      die();
    }
    if (is_array($result)===false){
      log::add('eleroha','debug','json result is not an array');
    	die();
    }

    if(array_key_exists('channel', $result)===false){
      log::add('eleroha','debug',"Key 'channel' not found in json array result");
      die();
    }
    if(array_key_exists('value', $result)===false){
      log::add('eleroha','debug',"Key 'value' not found in json array result");
      die();
    }
    if(array_key_exists('eqlogic_id', $result)===false){
      log::add('eleroha','debug',"Key 'eqlogic_id' not found in json array result");
      die();
    }

    $result['value_hr']=__('Etat inconnu', __FILE__)
    switch ($result['value']) {
      case '00':
        $result['value_hr']=__('Aucune information', __FILE__);
        break;
      case '01':
        $result['value_hr']=__('Ouvert', __FILE__);
        break;
      case '02':
        $result['value_hr']=__('Fermé', __FILE__);
        break;
      case '03':
        $result['value_hr']=__('Intermédiaire', __FILE__);
        break;
      case '04':
        $result['value_hr']=__('Ventilation', __FILE__);
        break;
      case '05':
        $result['value_hr']=__('Equipement bloqué', __FILE__);
        break;
      case '06':
        $result['value_hr']=__('Surchauffe', __FILE__);
        break;
      case '07':
        $result['value_hr']=__('Timeout', __FILE__);
        break;
      case '08':
        $result['value_hr']=__('Début ouverture', __FILE__);
        break;
      case '09':
        $result['value_hr']=__('Début fermeture', __FILE__);
        break;
      case '0a':
        $result['value_hr']=__('Ouverture', __FILE__);
        break;
      case '0b':
        $result['value_hr']=__('Fermeture', __FILE__);
        break;
      case '0d':
        $result['value_hr']=__('Arrêté position indéfinie', __FILE__);
        break;
      case '0e':
        $result['value_hr']=__('Top position stop wich is tilt position', __FILE__);
        break;
      case '0f':
        $result['value_hr']=__('Bottom position stop wich is intermediate position', __FILE__);
        break;
      case '10':
        $result['value_hr']=__('Equipement éteint', __FILE__);
        break;
      case '11':
        $result['value_hr']=__('Equipement allumé', __FILE__);
        break;
      default:
        $result['value_hr']=__('Etat inconnu', __FILE__);
    }

    $eleroha = eleroha::byId($result['eqlogic_id']);
    if (is_object($eleroha)) {
      $eleroha->checkAndUpdateCmd('info', $result['value']);
      $eleroha->checkAndUpdateCmd('info_hr', $result['value_hr']);
      log::add('eleroha','debug','Obj found, saving Etat: '.$result['value'] . ' ('.$result['value_hr'].')');
      $eleroha->refreshWidget();
    }else{
      log::add('eleroha','debug','Obj NO found, failed to save Etat: '.$result['info']['value']);
      die();
    }
} catch (Exception $e) {
    log::add('eleroha', 'error', displayException($e));
}
