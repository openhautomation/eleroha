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
require_once dirname(__FILE__) . '/../../../core/php/core.inc.php';

function eleroha_install() {
  message::add('eleroha', '**** install called', null, null);
  if (config::byKey('api::eleroha::mode') != 'localhost') {
    config::save('api::eleroha::mode', 'localhost');
  }
}

function eleroha_update() {
  message::add('eleroha', '**** update called', null, null);

  if (config::byKey('api::eleroha::mode') != 'localhost') {
    config::save('api::eleroha::mode', 'localhost');
  }

  foreach (eqLogic::byType('eleroha') as $eqLogic) {

    $elerohaCmd = $eqLogic->getCmd(null, "info");
    if (is_object($elerohaCmd)){
      $elerohaCmd->remove();
    }

    $elerohaCmd = $eqLogic->getCmd(null, "value");
    if (!is_object($elerohaCmd)){
      $elerohaCmd=new cmd();
      $elerohaCmd->setEqLogic_id($eqLogic->getId());
      $elerohaCmd->setLogicalId("value");
      $elerohaCmd->setName("Valeur");
      $elerohaCmd->setType("info");
      $elerohaCmd->setSubType("string");
      $elerohaCmd->setIsHistorized(0);
      $elerohaCmd->setIsVisible(0);
      $elerohaCmd->save();
    }
    $elerohaCmd = $eqLogic->getCmd(null, "status");
    if (!is_object($elerohaCmd)){
      $elerohaCmd=new elerohaCmd();
      $elerohaCmd->setEqLogic_id($eqLogic->getId());
      $elerohaCmd->setLogicalId("status");
      $elerohaCmd->setName("Etat");
      $elerohaCmd->setType("info");
      $elerohaCmd->setSubType("string");
      $elerohaCmd->setIsHistorized(0);
      $elerohaCmd->setIsVisible(1);
      $elerohaCmd->save();
    }
  }

  $eleroha_path=dirname(__FILE__, 2) . "/resources/elerohad/";
  if(file_exists($eleroha_path . "globals.py")===true){
    unlink($eleroha_path . "globals.py");
    log::add('eleroha', 'debug', "elerohad globals.py deleted");
  }
  if(file_exists($eleroha_path . "globals.pyc")===true){
    unlink($eleroha_path . "globals.pyc");
    log::add('eleroha', 'debug', "elerohad globals.pyc deleted");
  }
  $eleroha_path=dirname(__FILE__, 2) . "/resources/elerohad/jeedom/";
  if(file_exists($eleroha_path . "__init__.pyc")===true){
    unlink($eleroha_path . "__init__.pyc");
    log::add('eleroha', 'debug', "elerohad __init__.pyc deleted");
  }
  if(file_exists($eleroha_path . "jeedom.pyc")===true){
    unlink($eleroha_path . "jeedom.pyc");
    log::add('eleroha', 'debug', "elerohad jeedom.pyc deleted");
  }
}

function eleroha_remove(){
}
?>
