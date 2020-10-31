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
header('Content-type: application/json');
require_once dirname(__FILE__) . "/../../../../core/php/core.inc.php";

if (!jeedom::apiAccess(init('apikey'), 'eleroha')) {
	echo 'Clef API non valide, vous n\'etes pas autorisé à effectuer cette action';
	die();
}

if (init('test') != '') {
	echo 'OK';
	die();
}

log::add('eleroha','debug','Received data from Deamond');

$deamon_message=file_get_contents("php://input");
if($deamon_message===false){
  log::add('eleroha','debug','Read deamon message failed');
  die();
}

log::add('eleroha','debug','Read deamon message: "'.$deamon_message.'"');
$result = json_decode($deamon_message, true);
if($result===false){
  log::add('eleroha','debug','json decode failed');
  die();
}
if (is_array($result)===false){
  log::add('eleroha','debug','json result is not an array');
	die();
}

if(array_key_exists('info', $result)===true){
  log::add('eleroha','debug','update from deamon value: '.$result['info']['value']);
  log::add('eleroha','debug','update from deamon channel: '.$result['info']['channel']);
  log::add('eleroha','debug','update from deamon EqLogic_id: '.$result['info']['EqLogic_id']);
  $eleroha = eleroha::byId($result['info']['EqLogic_id']);
  if (is_object($eleroha)) {
    $eleroha->checkAndUpdateCmd('info', $result['info']['value']);
    log::add('eleroha','debug','Obj found, saving Etat: '.$result['info']['value']);
    //$cmd = $eleroha->getCmd(null, 'info');
    //$cmd->event($result['info']['value']);
    //$cmd->save();
    $eleroha->refreshWidget();
  }else{
    log::add('eleroha','debug','Obj NO found, failed to save Etat: '.$result['info']['value']);
  }
}
