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

/* * ***************************Includes********************************* */
require_once __DIR__  . '/../../../../core/php/core.inc.php';

class eleroha extends eqLogic {

  public static function deamon_info(){
    log::add('eleroha', 'debug', __FUNCTION__ . '()-ln:'.__LINE__.' Called');
    $return = array();
    $return['log'] = 'eleroha';
    $return['state'] = 'nok';
    $pid_file = jeedom::getTmpFolder('eleroha') . '/deamon.pid';
    if (file_exists($pid_file)) {
			$pid = trim(file_get_contents($pid_file));
			if (is_numeric($pid) && posix_getsid($pid)) {
				$return['state'] = 'ok';
			} else {
				shell_exec(system::getCmdSudo() . 'rm -rf ' . $pid_file . ' 2>&1 > /dev/null;rm -rf ' . $pid_file . ' 2>&1 > /dev/null;');
			}
		}
    $return['launchable'] = 'ok';
    $port = config::byKey('port', 'eleroha');
		$port = jeedom::getUsbMapping($port);
		if (is_string($port)) {
			if (@!file_exists($port)) {
				$return['launchable'] = 'nok';
				$return['launchable_message'] = __('Le port n\'est pas configuré', __FILE__);
			}
			exec(system::getCmdSudo() . 'chmod 777 ' . $port . ' > /dev/null 2>&1');
		}

    return $return;
	}

  public static function deamon_start($_debug = false){
    log::add('eleroha', 'debug', __FUNCTION__ . '()-ln:'.__LINE__.' Called');
    self::deamon_stop();
    $deamon_info = self::deamon_info();
    if ($deamon_info['launchable'] != 'ok') {
      throw new Exception(__('Veuillez vérifier la configuration', __FILE__));
    }

    $port = config::byKey('port', 'eleroha');
    if ($port != 'auto') {
      $port = jeedom::getUsbMapping($port);
    }
    $eleroha_path = realpath(dirname(__FILE__) . '/../../resources/elerohad');
    log::add('eleroha', 'debug', __FUNCTION__ . '()-ln:'.__LINE__.' deamon path: ' .$eleroha_path );

    $protocol = trim($protocol, ',');
    $cmd = '/usr/bin/python ' . $eleroha_path . '/elerohad.py';
    $cmd .= ' --loglevel ' . log::convertLogLevel(log::getLogLevel('eleroha'));
		$cmd .= ' --device ' . $port;
		$cmd .= ' --socketport ' . config::byKey('socketport', 'eleroha');
		$cmd .= ' --sockethost 127.0.0.1';
    $cmd .= ' --callback ' . network::getNetworkAccess('internal', 'proto:127.0.0.1:port:comp') . '/plugins/eleroha/core/php/jeeEleroha.php';
		$cmd .= ' --apikey ' . jeedom::getApiKey('eleroha');
		$cmd .= ' --pid ' . jeedom::getTmpFolder('eleroha') . '/deamon.pid';
    log::add('eleroha', 'info', 'Démarrage du démon eleroha : ' . $cmd);
    exec($cmd . ' >> ' . log::getPathToLog('eleroha') . ' 2>&1 &');
    $i = 0;
    while ($i < 30) {
      $deamon_info = self::deamon_info();
      if ($deamon_info['state'] == 'ok') {
        break;
      }
      sleep(1);
      $i++;
    }
    if ($i >= 30) {
      log::add('eleroha', 'error', 'Impossible de démarrer le démon eleroha, vérifiez le log eleroha', 'unableStartDeamon');
      return false;
    }
    message::removeAll('eleroha', 'unableStartDeamon');
    sleep(2);
    config::save('include_mode', 0, 'eleroha');
    log::add('eleroha', 'info', 'Démon eleroha demarré');
    return true;
  }

  public static function deamon_stop(){
    log::add('eleroha', 'debug', __FUNCTION__ . '()-ln:'.__LINE__.' Called');
    $pid_file = jeedom::getTmpFolder('eleroha') . '/deamon.pid';
    if (file_exists($pid_file)) {
      $pid = intval(trim(file_get_contents($pid_file)));
      system::kill($pid);
    }
    system::kill('elerohad.py');
    system::fuserk(config::byKey('socketport', 'eleroha'));
    $port = config::byKey('port', 'eleroha');
    system::fuserk(jeedom::getUsbMapping($port));
    sleep(1);
  }

  public static function sendIdToDeamon() {
    foreach (self::byType('eleroha') as $eqLogic) {
      $eqLogic->allowDevice();
      usleep(500);
    }
  }

	public static function dependancy_install() {
		log::remove(__CLASS__ . '_update');
		return array('script' => dirname(__FILE__) . '/../../resources/install_#stype#.sh ' . jeedom::getTmpFolder('eleroha') . '/dependance', 'log' => log::getPathToLog(__CLASS__ . '_update'));
	}

  public static function dependancy_info() {
		$return = array();
		$return['progress_file'] = jeedom::getTmpFolder('eleroha') . '/dependance';
		if (exec(system::getCmdSudo() . system::get('cmd_check') . '-E "python3\-serial|python3\-requests|python3\-pyudev" | wc -l') >= 3) {
			$return['state'] = 'ok';
		} else {
			$return['state'] = 'nok';
		}
		return $return;
	}

    /*     * ***********************Methode static*************************** */

    /*
     * Fonction exécutée automatiquement toutes les minutes par Jeedom
      public static function cron() {

      }
     */

    /*
     * Fonction exécutée automatiquement toutes les 15 minutes par Jeedom
      public static function cron15() {

      }
     */


    /*
     * Fonction exécutée automatiquement toutes les heures par Jeedom
      public static function cronHourly() {

      }
     */

    /*
     * Fonction exécutée automatiquement tous les jours par Jeedom
      public static function cronDaily() {

      }
     */

    /*     * *********************Méthodes d'instance************************* */
    private function getMotorStructure(&$motorStructure){
      log::add('eleroha', 'debug', __FUNCTION__ . '()-ln:'.__LINE__.' Called');

      $motorStructure=array(
        //Set motor Up
        'up'=>array(
          'name'=>__('Monter', __FILE__),
          'id'=>'up',
          'type'=>'action',
          'subtype'=>'other',
          'message_placeholder'=> __('Monter', __FILE__),
          'title_disable'=> 1,
          'historized'=>0,
          'visible'=>1,
          'configuration'=>array(array('k1'=>'actionCmd', 'k2'=>'setup'), array('k1'=>'device', 'k2'=>'')),
          'unite'=>''
        ),
        //Set motor Down
        'down'=>array(
          'name'=>__('Descendre', __FILE__),
          'id'=>'down',
          'type'=>'action',
          'subtype'=>'other',
          'message_placeholder'=> __('Descendre', __FILE__),
          'title_disable'=> 1,
          'historized'=>0,
          'visible'=>1,
          'configuration'=>array(array('k1'=>'actionCmd', 'k2'=>'setdown'), array('k1'=>'device', 'k2'=>'')),
          'unite'=>''
        ),
        //Set motor Stop
        'stop'=>array(
          'name'=>__('Stop', __FILE__),
          'id'=>'stop',
          'type'=>'action',
          'subtype'=>'other',
          'message_placeholder'=> __('Stop', __FILE__),
          'title_disable'=> 1,
          'historized'=>0,
          'visible'=>1,
          'configuration'=>array(array('k1'=>'actionCmd', 'k2'=>'setstop'), array('k1'=>'device', 'k2'=>'')),
          'unite'=>''
        ),
        //Set motor Tilt position
        'tilt'=>array(
          'name'=>__('Ventillation', __FILE__),
          'id'=>'tilt',
          'type'=>'action',
          'subtype'=>'other',
          'message_placeholder'=> __('Ventillation', __FILE__),
          'title_disable'=> 1,
          'historized'=>0,
          'visible'=>1,
          'configuration'=>array(array('k1'=>'actionCmd', 'k2'=>'settilt'), array('k1'=>'device', 'k2'=>'')),
          'unite'=>''
        ),
        //Set motor Intermediate position
        'intermediate'=>array(
          'name'=>__('Intermédiaire', __FILE__),
          'id'=>'intermediate',
          'type'=>'action',
          'subtype'=>'other',
          'message_placeholder'=> __('Intermédiaire', __FILE__),
          'title_disable'=> 1,
          'historized'=>0,
          'visible'=>1,
          'configuration'=>array(array('k1'=>'actionCmd', 'k2'=>'setintermediate'), array('k1'=>'device', 'k2'=>'')),
          'unite'=>''
        ),
        // Etat row
        'value'=>array(
          'name'=>__('Valeur', __FILE__),
          'id'=>'value',
          'parent'=>'0',
          'type'=>'info',
          'subtype'=>'string',
          'historized'=>0,
          'visible'=>0,
          'configuration'=>array(),
          'unite'=>''
        ),
        // Etat human readable
        'status'=>array(
          'name'=>__('Etat', __FILE__),
          'id'=>'status',
          'parent'=>'0',
          'type'=>'info',
          'subtype'=>'string',
          'historized'=>0,
          'visible'=>1,
          'configuration'=>array(),
          'unite'=>''
        ),
        //Refesh action
        'refresh'=>array(
          'name'=>__('Rafraichir', __FILE__),
          'id'=>'refresh',
          'parent'=>'0',
          'type'=>'action',
          'subtype'=>'other',
          'historized'=>0,
          'visible'=>1,
          'configuration'=>array(array('k1'=>'actionCmd', 'k2'=>'getinfo'), array('k1'=>'device', 'k2'=>'')),
          'unite'=>''
        )
      );
    }

    public function preInsert() {

    }

    public function postInsert() {

    }

    public function preSave() {

    }

    public function postSave() {

    }

    public function preUpdate() {
      log::add('eleroha', 'debug', __FUNCTION__ . '()-ln:'.__LINE__.' Called');
      if (empty($this->getConfiguration('channel'))) {
        throw new Exception(__('Vous avez oublié de saisir le channel de votre équipement',__FILE__));
      }
    }

    public function postUpdate() {
      log::add('eleroha', 'debug', __FUNCTION__ . '()-ln:'.__LINE__.' Called');
      $this->getMotorStructure($motorStructure);

      foreach ($motorStructure as $key => $value) {
        log::add('eleroha', 'debug', __FUNCTION__ . '()-ln: '.$value['name'].' in process');

        $elerohaCmd = $this->getCmd(null, $value['id']);
        if (!is_object($elerohaCmd)){
          $elerohaCmd=new elerohaCmd();
          $elerohaCmd->setLogicalId($value['id']);
          log::add('eleroha', 'debug', __FUNCTION__ . '()-ln: '.$value['name'].' created');
        }

        $elerohaCmd->setName($value['name']);
        $elerohaCmd->setEqLogic_id($this->id);
        for($i=0;$i<count($value['configuration']);$i++){
          if($value['configuration'][$i]['k1']=='device'){
            $elerohaCmd->setConfiguration($value['configuration'][$i]['k1'], $this->getConfiguration('channel'));
          }else{
            $elerohaCmd->setConfiguration($value['configuration'][$i]['k1'], $value['configuration'][$i]['k2']);
          }
        }
        $elerohaCmd->setType($value['type']);
        $elerohaCmd->setSubType($value['subtype']);
        $elerohaCmd->setIsHistorized($value['historized']);
        $elerohaCmd->setIsVisible($value['visible']);
        if(trim($value['unite'])!=''){
          $elerohaCmd->setUnite($value['unite']);
        }
        if(array_key_exists('message_placeholder', $value)===true){
          $elerohaCmd->setDisplay('message_placeholder', $value['message_placeholder']);
        }
        if(array_key_exists('title_disable', $value)===true){
          $elerohaCmd->setDisplay('title_disable', $value['title_disable']);
        }

        $elerohaCmd->save();
        log::add('eleroha', 'debug', __FUNCTION__ . '()-ln: '.$value['name'].' saved');
        unset($elerohaCmd);
      }
      unset($value);
      unset($motorStructure);
    }

    public function preRemove() {

    }

    public function postRemove() {

    }

    /*
     * Non obligatoire mais permet de modifier l'affichage du widget si vous en avez besoin
      public function toHtml($_version = 'dashboard') {

      }
     */

    /*
     * Non obligatoire mais ca permet de déclencher une action après modification de variable de configuration
    public static function postConfig_<Variable>() {
    }
     */

    /*
     * Non obligatoire mais ca permet de déclencher une action avant modification de variable de configuration
    public static function preConfig_<Variable>() {
    }
     */

    /*     * **********************Getteur Setteur*************************** */
}

class elerohaCmd extends cmd {
    /*
     * Non obligatoire permet de demander de ne pas supprimer les commandes même si elles ne sont pas dans la nouvelle configuration de l'équipement envoyé en JS
      public function dontRemoveCmd() {
      return true;
      }
     */

    public function execute($_options = array()) {

      $eqLogic = $this->getEqlogic();
      log::add('eleroha', 'debug',  __FUNCTION__ . '()-ln:'.__LINE__.' LogicalId: '. $this->getLogicalId());
      log::add('eleroha', 'debug',  __FUNCTION__ . '()-ln:'.__LINE__.' EqLogic_id: '. $this->getEqLogic_id());
      log::add('eleroha', 'debug',  __FUNCTION__ . '()-ln:'.__LINE__.' options: '. json_encode($_options));

      if ( $this->GetType = "action" ){
        log::add('eleroha', 'debug', __FUNCTION__ . '()-ln:'.__LINE__.' Action: '.$this->getConfiguration('actionCmd'));
        switch ($this->getConfiguration('actionCmd')) {
          case 'getinfo':
          case 'setup':
          case 'setdown':
          case 'setstop':
          case 'settilt':
          case 'setintermediate':
            $data=array('apikey'=> jeedom::getApiKey('eleroha'), 'cmd' => $this->getConfiguration('actionCmd'), 'queueing'=>config::byKey('queueing', 'eleroha'), 'device' => array('id'=>$this->getConfiguration('device'), 'EqLogic_id'=>$this->getEqLogic_id(), 'cmd'=>$this->getConfiguration('actionCmd')));
            $message = trim(json_encode($data));

            log::add('eleroha', 'debug', __FUNCTION__ . '()-ln:'.__LINE__.' Data send: '.$message);
            $socket = socket_create(AF_INET, SOCK_STREAM, 0);
            if($socket===false){
              $errorcode = socket_last_error();
              $errormsg = socket_strerror($errorcode);
              throw new Exception(__('Creation du socket impossible: '.$errormsg, __FILE__));
            }
            if(socket_connect($socket, '127.0.0.1', config::byKey('socketport', 'eleroha'))===false){
              $errorcode = socket_last_error();
              $errormsg = socket_strerror($errorcode);
              throw new Exception(__('Connexion au socket impossible: '.$errormsg, __FILE__));
            }
            if(socket_write($socket, trim($message), strlen(trim($message)))===false){
              $errorcode = socket_last_error();
              $errormsg = socket_strerror($errorcode);
              throw new Exception(__('Ecriture sur le socket impossible: '.$errormsg, __FILE__));
            }
            socket_close($socket);

            break;
          default:
            throw new Exception(__('Commande non implémentée actuellement', __FILE__));
        }
      }else{
        throw new Exception(__('Commande non implémentée actuellement', __FILE__));
      }
    }

    /*     * **********************Getteur Setteur*************************** */
}
