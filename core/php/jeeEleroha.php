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

    $eleroha = eleroha::byId($result['eqlogic_id']);
    if (is_object($eleroha)) {
      $eleroha->checkAndUpdateCmd('info', $result['value']);
      log::add('eleroha','debug','Obj found, saving Etat: '.$result['value']);
      $eleroha->refreshWidget();
    }else{
      log::add('eleroha','debug','Obj NO found, failed to save Etat: '.$result['info']['value']);
      die();
    }
} catch (Exception $e) {
    log::add('eleroha', 'error', displayException($e));
}
