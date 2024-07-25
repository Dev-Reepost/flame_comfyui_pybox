import os
import datetime
import uuid
import shutil
import tempfile
from enum import Enum
from pathlib import Path
from pprint import pprint
import pybox_v1 as pybox

from comfyui_client import COMFYUI_HOSTNAME
from comfyui_client import COMFYUI_HOSTPORT
from comfyui_client import COMFYUI_WORKING_DIR
from comfyui_client import COMFYUI_WORKFLOW_DIR
from comfyui_client import COMFYUI_WORKFLOW_PATH
from comfyui_client import COMFYUI_IO_DIR
from comfyui_client import COMFYUI_SERVER_INPUT_DIR
from comfyui_client import COMFYUI_SERVER_OUTPUT_DIR

from comfyui_client import DEFAULT_IMAGE_FORMAT

from comfyui_client import queue_prompt
from comfyui_client import prompt_execution
from comfyui_client import interrupt_execution
from comfyui_client import ComfyUIStatus


DEFAULT_IMAGE_WIDTH = 1920
DEFAULT_IMAGE_HEIGHT = 1080
IMAGE_WIDTH_MAX = 7680 
IMAGE_HEIGHT_MAX = 4320 
def EMPTY_IMAGE_FILEPATH(color):
    filename = color + "_1-1." + DEFAULT_IMAGE_FORMAT
    return str(Path(COMFYUI_WORKING_DIR) / "presets" / filename)

FRAME_PTTRN = "<FRAME>"
VERSION_PTTRN = "<VERSION>"
OPERATOR_PTTRN = "<OPERATOR>"

UI_HOSTNAME = "Hostname"
UI_HOSTPORT = "Hostport"

UI_WORKFLOW_PATH = "Workflow path"

UI_SUBMIT = "Process"
UI_VERSION = "Version"
UI_INCVER = "New Version"
UI_INTERRUPT = "Interrupt"

UI_OUT_WIDTH = "Width"
UI_OUT_HEIGHT = "Height"

UI_PROMPT_PREFIX = "Prompt"
def UI_PROMPT(orientation, p):
    return " ".join([UI_PROMPT_PREFIX, orientation, str(p)]) 


class Color(list, Enum):
    RED = [1.0, 0.0, 0.0]
    GREEN = [0.0, 1.0, 0.0]
    BLUE = [0.0, 0.0, 1.0]
    YELLOW = [1.0, 1.0, 0.0]
    GRAY = [0.14, 0.14, 0.14]

class EndPoint(str, Enum):
    IN = "in"
    OUT = "out"

class LayerIn(str, Enum):
    FRONT = "Front"
    BACK = "Back"
    MATTE = "Matte"
    NORMAL = "Normal"
    ZDEPTH = "ZDepth"

class LayerOut(str, Enum):
    RESULT = "Result"
    OUTMATTE = "OutMatte"
    OUTZDEPTH = "OutZDepth"
    OUTNORMAL = "OutNormal"

class PromptSign(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

class Status(str, Enum):
    IDLE = "Idle"
    WAITING = "Waiting"
    EXECUTING = "Executing"
    PROCESSED = "Processed"
    FAILED = "Failed"


class ComfyUIBaseClass(pybox.BaseClass):
    hostname = ""
    hostport = ""
    server_address = ""
    server_url = ""

    operator_name = ""
    operator_layers = [LayerIn.FRONT, LayerOut.RESULT]
    operator_static = False
    
    workflow_dir = ""
    workflow_path = ""
    workflow = {}
    workflow_id_to_class_type = {}
    workflow_load_exr_front_idx = -1
    workflow_save_exr_outmatte_idx = -1
    workflow_save_exr_result_idx = -1
    
    prompt_id = ""
    client_id = ""
    
    processing = False
    force_processing = False
    
    ui_processing = Status.IDLE
    ui_version = UI_VERSION
    ui_processing_color_row = -1
    ui_processing_color_col = -1
    ui_version_row = -1
    ui_version_col = -1
    
    image_format = DEFAULT_IMAGE_FORMAT
    
    basename = ""
    in_front_basename = ""
    in_front_filename_pttrn = ""
    in_front_filepath_pttrn = ""
    in_default_filepath = EMPTY_IMAGE_FILEPATH("black")
    out_result_basename = ""
    out_result_filepath_pttrn = ""
    out_matte_basename = ""
    out_matte_filepath_pttrn = ""
    out_default_filepath = EMPTY_IMAGE_FILEPATH("black")
    
    version_padding = 3
    frame_padding = 4
    
    
    ###################################
    # Server
    
    def init_host_info(self):
        self.hostname = COMFYUI_HOSTNAME
        self.hostport = COMFYUI_HOSTPORT
        self.set_server_address()
    
    
    def set_host_info(self):
        self.hostname = self.get_global_element_value(UI_HOSTNAME)
        self.hostport = self.get_global_element_value(UI_HOSTPORT)
        self.set_server_address()
    
    
    def set_server_address(self):
        self.server_address = self.hostname + ":" + self.hostport
        self.server_url = "http://" + self.server_address
    
    
    def init_client(self):
        self.client_id = str(uuid.uuid4())

    
    ###################################
    # Project 

    
    def get_frame_str(self):
        return self.pad(self.get_frame(), self.frame_padding)
    
    
    def get_version_str(self):
        return self.pad(self.version, self.version_padding)
    
    
    def pad(self, elem, padding):
        return str(elem).zfill(padding)
    
    
    def print_project_metadata(self):
        print(f'Project: {self.get_project()}')
        print(f'Resolution: {self.get_resolution()}')
    
    
    def print_node_metadata(self):
        print(f'Node: {self.get_node_name()}')
        print(f'Operator: {self.operator_name}')
    
    
    def print_frame_metadata(self):
        print(f'Frame: {self.get_frame_str()}')
        print(f'Version: {self.get_version_str()}')
    
    
    def print_flame_metadata(self):
        self.print_project_metadata()
        self.print_node_metadata()
        self.print_frame_metadata()
    
    
    def print_date_time(self):
        now = datetime.datetime.now()
        print(now.strftime("%Y-%m-%d %H:%M:%S"))
    
    
    ###################################
    # UI
    
    
    def init_ui(self):
        raise NotImplementedError("init_ui method not implemented")
    
    
    def set_ui_host_info(self, col):
        self.set_ui_hostname(row=0, col=col)
        self.set_ui_hostport(row=1, col=col)
    
    
    def set_ui_hostname(self, row, col):
        host_ip_tf = pybox.create_text_field(
            UI_HOSTNAME, 
            row=row, col=col, 
            value=COMFYUI_HOSTNAME
            )
        self.add_global_elements(host_ip_tf)

    
    def set_ui_hostport(self, row, col):
        host_port_tf = pybox.create_text_field(
            UI_HOSTPORT, 
            row=row, col=col, 
            value=COMFYUI_HOSTPORT
            )
        self.add_global_elements(host_port_tf)
    
    
    def set_ui_workflow_path(self, col, workflow_dir, workflow_path):
        wfapi_path = pybox.create_file_browser(
            UI_WORKFLOW_PATH, 
            workflow_path, "json", 
            home=workflow_dir, 
            row=2, col=col, 
            tooltip="Workflow path"
            )
        self.add_global_elements(wfapi_path)
    
    
    def set_ui_versions(self):
        versions = self.get_version_list(self.version)
        ui_uuid = self.get_project() + self.get_node_name() + str(len(versions))
        self.ui_version = "         " + UI_VERSION + "         " + ui_uuid
        versions_list = pybox.create_popup(
            self.ui_version,
            versions,
            value=self.version-1, 
            default=0, 
            row=self.ui_version_row, 
            col=self.ui_version_col, 
            tooltip="Versions"
            )
        self.add_global_elements(versions_list)
    
    
    def set_ui_increment_version(self, row, col):
        wfapi_submit = pybox.create_toggle_button(
            UI_INCVER, False, default=False, 
            row=row, col=col, tooltip="Increment version"
            )
        self.add_global_elements(wfapi_submit)
        
        
    def set_ui_submit(self, row, col):
        wfapi_submit = pybox.create_toggle_button(
            UI_SUBMIT, False, default=False, 
            row=row, col=col, tooltip="Queue workflow on ComfyUI server"
            )
        self.add_global_elements(wfapi_submit)
    
    
    def set_ui_interrupt(self, row, col):
        wfapi_intrrpt = pybox.create_toggle_button(
            UI_INTERRUPT, False, default=False, 
            row=row, col=col, tooltip="Interrupt workfow execution"
            )
        self.add_global_elements(wfapi_intrrpt)
    
        
    def set_ui_processing_color(self, color, status):
        if self.get_global_element(self.ui_processing):
            self.remove_global_element(self.ui_processing)
        self.ui_processing = status
        wfapi_proc = pybox.create_color(
            status, 
            values=color, 
            default=Color.GRAY,
            row=self.ui_processing_color_row, 
            col=self.ui_processing_color_col,
            tooltip="Workflow execution state on server"
            )
        self.add_global_elements(wfapi_proc)
    
    
    ###################################
    # Workflow 
    
    
    def set_models(self):
        raise NotImplementedError("set_models method not implemented")
    
    
    def workflow_setup(self):
        raise NotImplementedError("workflow_setup method not implemented")
    
    
    def load_workflow(self):
        raise NotImplementedError("load_workflow method not implemented")
    
    
    def init_workflow(self):
        self.workflow_dir = COMFYUI_WORKFLOW_DIR(self.operator_name)
        self.workflow_path = COMFYUI_WORKFLOW_PATH(self.operator_name)
    
    
    def get_workflow_index(self, class_type):
        return [key for key, value in self.workflow_id_to_class_type.items() if value == class_type][0]

    
    def get_workflow_node_attribute(self, index, field):
        self.workflow.get(index)["inputs"][field]


    def set_workflow_load_exr_filepath(self, layers=[LayerIn.FRONT]):
        if self.workflow:
            if LayerIn.FRONT in layers:
                front_filepath_pttrn = Path(COMFYUI_SERVER_INPUT_DIR) / self.get_project()  / OPERATOR_PTTRN / self.in_front_filename_pttrn
                operator = self.operator_name
                version = self.get_version_str()
                frame = self.get_frame_str()
                front_filepath = self.instanciate_filepath(front_filepath_pttrn, operator, version, frame)
                print(f"Workflow LoadEXR front filepath {front_filepath}")
                self.workflow.get(self.workflow_load_exr_front_idx)["inputs"]["filepath"] = str(front_filepath)
    
    
    def set_workflow_save_exr_filename_prefix(self, layers=[LayerOut.RESULT, LayerOut.OUTMATTE]):
        if self.workflow: 
            version = self.get_version()
            frame = self.get_frame() if not self.operator_static else 0
            dir_path = Path(COMFYUI_SERVER_OUTPUT_DIR) / self.get_project() / self.operator_name / self.get_version_str() 
            if LayerOut.RESULT in layers:
                result_filepath = str(dir_path / self.out_result_basename)
                print(f"Workflow SaveEXR result filepath {result_filepath} - v{version} - f{frame}")
                self.workflow.get(self.workflow_save_exr_result_idx)["inputs"]["filename_prefix"] = result_filepath
                self.workflow.get(self.workflow_save_exr_result_idx)["inputs"]["version"] = version
                self.workflow.get(self.workflow_save_exr_result_idx)["inputs"]["start_frame"] = frame
            if LayerOut.OUTMATTE in layers:
                matte_filepath = str(dir_path / self.out_matte_basename)
                print(f"Workflow SaveEXR out matte filepath {matte_filepath} - v{version} - f{frame}")
                self.workflow.get(self.workflow_save_exr_outmatte_idx)["inputs"]["filename_prefix"] = matte_filepath
                self.workflow.get(self.workflow_save_exr_outmatte_idx)["inputs"]["version"] = version
                self.workflow.get(self.workflow_save_exr_outmatte_idx)["inputs"]["start_frame"] = frame
    
    
    def prepare_workflow_execution(self):
        self.update_inputs(layers=self.operator_layers)
    
    
    def submit_workflow(self):
        operator = self.operator_name
        layer = LayerOut.RESULT
        version = self.get_version_str()
        frame = self.get_frame_str() if not self.operator_static else self.pad(0, self.frame_padding)
        if self.frame_exists(operator, layer, version, frame):
            if not self.force_processing:
                return
            else:
                self.increment_version()
        if self.workflow:
            self.set_host_info()
            print("Workflow submission")
            print("____________________")
            self.print_date_time()
            print("____________________")
            print("Workflow preparation")
            self.prepare_workflow_execution()
            print("Workflow instanciation")
            self.workflow_setup()
            print(f'Workflow queueing on {self.server_address} with client id {self.client_id}')
            self.prompt_id = queue_prompt(self.workflow, self.client_id, server_address=self.server_address)
            print(f'Workflow assigned prompt id {self.prompt_id}')
            if self.prompt_id:
                self.processing = True
    
    
    def interrupt_workflow(self):
        if self.client_id and self.processing:
            if self.prompt_id:
                self.set_host_info()
                print("Workflow execution interruption")
                print("____________________")
                response = interrupt_execution(self.prompt_id, self.client_id, self.server_address)
                print(f"Workflow execution interrupted on server {self.server_address} ({response})")
            self.processing = False
            self.set_global_element_value(UI_SUBMIT, False)
            self.set_ui_processing_color(Color.GRAY, Status.IDLE)
        self.set_global_element_value(UI_INTERRUPT, False)
        self.force_processing = False
    
    
    def update_workflow_execution(self):
        if self.client_id and self.prompt_id:
            self.set_host_info()
            print(f'Workflow execution status')
            while(True):
                response = prompt_execution(self.server_address, self.client_id, self.prompt_id["prompt_id"])
                if response:
                    self.processing = bool(response["node"] and 
                                            response["node"]["type"] in [ComfyUIStatus.EXECUTING, 
                                                                        ComfyUIStatus.EXECUTION_CACHED])
                    if self.processing:
                        self.set_ui_processing_color(Color.BLUE, Status.EXECUTING)
                    else:
                        self.set_ui_processing_color(Color.GREEN, Status.PROCESSED)
                        break
                else:
                    self.processing = False
                    self.set_global_element_value(UI_SUBMIT, False)
                    self.set_ui_processing_color(Color.RED, Status.FAILED)
                    break
        else:
            if self.processing:
                self.processing = False
                self.set_ui_processing_color(Color.RED, Status.FAILED)
                self.set_global_element_value(UI_SUBMIT, False)
            else:
                self.set_ui_processing_color(Color.GRAY, Status.IDLE)
    
    
    ###################################
    # I/O
    
    def get_project_path(self, end_point):
        project = self.get_project().upper()
        return Path(COMFYUI_IO_DIR[end_point]) / project 
    
    
    def get_operator_path(self, side):
        return self.get_project_path(side) / self.operator_name 
    
    
    def get_version_path(self, side=EndPoint.OUT):
        return self.get_operator_path(side) / self.get_version_str()
    
    
    def set_basename(self):
        self.basename = "_".join([self.get_project(), self.get_node_name()])
    

    def instanciate_filepath(self, filepath_pttrn, operator, version, frame):
        filepath = str(filepath_pttrn).replace(OPERATOR_PTTRN, operator)
        filepath = filepath.replace(FRAME_PTTRN, frame)
        return Path(filepath.replace(VERSION_PTTRN, version))
    
    
    ###################################
    # Inputs
    
    
    def set_in_front_basename(self):
        self.in_front_basename = "_".join([self.basename, LayerIn.FRONT])
        self.in_front_filename_pttrn = self.in_front_basename + "." + FRAME_PTTRN + "." + self.get_img_format()
    
    
    def set_in_front_filepath_pttrn(self):
        self.in_front_filepath_pttrn = str(self.get_project_path(EndPoint.IN) / self.operator_name / self.in_front_filename_pttrn)
    
    
    def get_in_socket_info(self, layer):
        if layer == LayerIn.FRONT:    
            socket_filename = self.in_front_basename + "." + self.get_img_format()
            src_filepath_pttrn = self.in_front_filepath_pttrn
            socket_idx = 0
            return (socket_filename, src_filepath_pttrn, socket_idx)
    
    
    def set_file_in(self, layers=[LayerIn.FRONT]):
        self.remove_in_sockets()
        in_layers = list(filter(lambda l: isinstance(l, LayerIn), layers))
        if not in_layers:
            self.set_in_socket(0, "undefined", "")
        else:
            self.get_operator_path(EndPoint.IN).mkdir(parents=True, exist_ok=True)
            for layer in in_layers:
                if layer == LayerIn.FRONT:
                    self.set_in_front_basename()
                    self.set_in_front_filepath_pttrn()
                    socket_filename, _, socket_idx = self.get_in_socket_info(layer)
                    socket_filepath = tempfile.gettempdir() + "/" + socket_filename
                    self.set_in_socket(socket_idx, layer, socket_filepath)
    
    
    def update_input(self, layer, socket_filename, dest_filepath_pattern, socket_idx):
        socket_filepath = Path(tempfile.gettempdir() + "/" + socket_filename)
        self.set_in_socket(socket_idx, layer, str(socket_filepath))
        print(f"Testing {str(socket_filepath)}")
        if socket_filepath.is_file():
            dest_filepath = dest_filepath_pattern.replace(FRAME_PTTRN, self.get_frame_str())
            print(f"Copying {socket_filepath} socket file")
            print(f"     to {dest_filepath}")
            shutil.copy(socket_filepath, dest_filepath)
        else:
            print(f"{layer} input socket file not found")
    
    
    def update_inputs(self, layers=[LayerIn.FRONT]):
        in_layers = list(filter(lambda l: isinstance(l, LayerIn), layers))
        for layer in in_layers:
            print(f"Updating {layer}")
            print("____________________")
            socket_filename, dest_filepath_pttrn, socket_idx = self.get_in_socket_info(layer)
            self.update_input(layer, socket_filename, dest_filepath_pttrn, socket_idx)
    
    
    ###################################
    # Outputs
    
    
    def out_frame_requested(self):
        return self.is_processing() and self.out_socket_active()
    

    def set_out_result_basename(self):
        self.out_result_basename = "_".join([self.basename, LayerOut.RESULT])
    
    
    def set_out_matte_basename(self):
        self.out_matte_basename = "_".join([self.basename, LayerOut.OUTMATTE])
    
    
    def set_out_result_filepath_pttrn(self):
        self.out_result_filepath_pttrn = self.set_out_filepath_pttrn(self.out_result_basename)
    
    
    def set_out_matte_filepath_pttrn(self):
        self.out_matte_filepath_pttrn = self.set_out_filepath_pttrn(self.out_matte_basename)
    
    
    def set_out_filepath_pttrn(self, basename):
        filename_pttrn = basename + "_v" + VERSION_PTTRN + "." + FRAME_PTTRN + "." + self.get_img_format()
        return str(self.get_project_path(EndPoint.OUT) / OPERATOR_PTTRN / VERSION_PTTRN / filename_pttrn)
    
    
    def get_out_socket_info(self, layer):
        if layer == LayerOut.RESULT:    
            socket_filename = self.out_result_basename + "." + self.get_img_format()
            src_filepath_pttrn = self.out_result_filepath_pttrn
            socket_idx = 0
        elif layer == LayerOut.OUTMATTE:
            socket_filename = self.out_matte_basename + "." + self.get_img_format()
            src_filepath_pttrn = self.out_matte_filepath_pttrn
            socket_idx = 1
        return (socket_filename, src_filepath_pttrn, socket_idx)
    
    
    def out_socket_active(self):
        return any([self.get_process_out_socket(self.get_out_socket_info(layer)[2])["active"]
                    for layer in self.operator_layers if isinstance(layer, LayerOut)])

    
    def set_file_out(self, layers=[LayerOut.RESULT]):
        self.remove_out_sockets()
        out_layers = list(filter(lambda l: isinstance(l, LayerOut), layers))
        if not out_layers:
            self.set_out_socket(0, "undefined", "")
        else:
            self.get_operator_path(EndPoint.OUT).mkdir(parents=True, exist_ok=True)
            for layer in out_layers:
                if layer == LayerOut.RESULT:
                    self.set_out_result_basename()
                    self.set_out_result_filepath_pttrn()            
                if layer == LayerOut.OUTMATTE:
                    self.set_out_matte_basename()
                    self.set_out_matte_filepath_pttrn()
                socket_filename, _, socket_idx = self.get_out_socket_info(layer)
                socket_filepath = tempfile.gettempdir() + "/" + socket_filename
                self.set_out_socket(socket_idx, layer, socket_filepath)
    
    
    def update_output(self, layer, filepath_pttrn, socket_filename, socket_idx):
        operator = self.operator_name
        version = self.get_version_str()
        frame = self.get_frame_str() if not self.operator_static else self.pad(0, self.frame_padding)
        src_filepath = self.instanciate_filepath(filepath_pttrn, operator, version, frame)
        print(f"Testing {str(src_filepath)}")
        if src_filepath.is_file():    
            socket_filepath = tempfile.gettempdir() + "/" + socket_filename
            self.set_out_socket(socket_idx, layer, socket_filepath)
            print(f"Copying {src_filepath}")
            print(f"     to {socket_filepath} socket file")
            shutil.copy(src_filepath, socket_filepath)
    

    def update_outputs(self, layers=[LayerOut.RESULT, LayerOut.OUTMATTE]):
        out_layers = list(filter(lambda l: isinstance(l, LayerOut), layers))
        for layer in out_layers:
            print(f"Updating {layer}")
            print("____________________")
            socket_filename, src_filepath_pttrn, socket_idx = self.get_out_socket_info(layer)
            self.update_output(layer, src_filepath_pttrn, socket_filename, socket_idx)
    
    
    def set_file_io(self):
        self.set_basename()
        self.set_img_format(self.image_format)
        self.init_version()
        self.set_file_in(layers=self.operator_layers)
        self.set_file_out(layers=self.operator_layers)
    
    
    def frame_exists(self, operator, layer, version, frame):
        if isinstance(layer, LayerOut):
            if layer == LayerOut.RESULT:
                filepath_pttrn = self.out_result_filepath_pttrn
            elif layer == LayerOut.OUTMATTE:
                filepath_pttrn = self.out_matte_filepath_pttrn
        elif isinstance(layer, LayerIn):
            if layer == LayerIn.FRONT:
                filepath_pttrn = self.in_front_filepath_pttrn
        if not filepath_pttrn:
            filepath_pttrn = self.out_result_filepath_pttrn
        filepath = self.instanciate_filepath(filepath_pttrn,  operator, version, frame)
        if filepath.is_file():
            return True
        return False
    
    
    def init_version(self):
        version = self.get_version_fs()
        print(f"SET VERSION TO {version}")
        self.set_version(version)
    
    
    def get_version(self):
        return self.version
    
    
    def set_version(self, version):
        self.version = version
        self.get_version_path(EndPoint.OUT).mkdir(parents=True, exist_ok=True)
        ui_version = self.get_global_element(self.ui_version)
        if ui_version and int(ui_version["value"]) != self.version:
            self.remove_global_element(self.ui_version)
            self.set_ui_versions()
    
    
    def get_version_fs(self): 
        operator_path = self.get_operator_path(EndPoint.OUT)
        print(operator_path)
        version_dir_paths = [p[0] for p in os.walk(operator_path)]
        version_dir_paths_sorted = sorted(version_dir_paths)
        if len(version_dir_paths_sorted) > 1:
            last_version_dir_path = version_dir_paths_sorted[-1]
            out_version = int(last_version_dir_path.split('/')[-1])
        else:
            out_version = 1    
        return out_version
    
    
    def get_version_list(self, version):
        return list(map(lambda e: self.pad(e, self.version_padding), range(1, version+1)))
    
    
    def increment_version(self):
        last_version = sorted(self.get_global_element(self.ui_version)["items"])[-1]
        inc_version = int(last_version) + 1
        self.set_version(inc_version)
        print(f"INCREMENT VERSION to {self.version}")
        self.set_global_element_value(UI_INCVER, False)
    
    
    ###########################################################################
    # Overrided functions from pybox.BaseClass
    
    
    def initialize(self):
        print("____________________")
        print("initialize")
        print("____________________")
        self.print_date_time()
        print("____________________")
        
        self.init_host_info()
        self.init_client()
        self.init_workflow()
        self.set_file_io()
        self.set_models()
        self.load_workflow()
        self.init_ui()

        self.print_flame_metadata()
    
    
    def setup_ui(self):
        print("____________________")
        print("setup_ui")
        print("____________________")
        self.print_date_time()
        print("____________________")
        
        self.print_flame_metadata()
    
    
    def execute(self):
        print("____________________")
        print("execute")
        print("____________________")
        self.print_date_time()
        print("____________________")
        
        for elem in self.get_ui_changes():
            if elem["name"] == self.ui_version:
                self.version = int(self.get_global_element_value(self.ui_version)) + 1
            elif elem["name"] == UI_INCVER:
                if self.get_global_element_value(UI_INCVER):
                    self.increment_version()
        
        self.print_flame_metadata()
    
        
    def teardown(self):
        print("____________________")
        print("teardown")
        print("____________________")
        self.print_date_time()
        print("____________________")
        