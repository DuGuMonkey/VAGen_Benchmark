import os
import time
import math

def run_fucntion_debug(ckt_type, Requirement_lines, VA_path):
    class FileList:
        def __init__(self, directory_path):
            self.directory_path = directory_path
            self.tb_mdls = self._parse_directory(directory_path)

        def _parse_directory(self, directory_path):
            scs_files = {}
            mdl_files = {}
            tb_mdls = []

            for root, _, files in os.walk(directory_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    name, ext = os.path.splitext(file)
                    if ext == ".scs":
                        scs_files[name] = full_path
                    elif ext == ".mdl":
                        mdl_files[name] = full_path

            for name in scs_files:
                if name in mdl_files:
                    tb_mdls.append((scs_files[name], mdl_files[name]))

            return tb_mdls
        
    #Execute spectremdl and finally return the file path of the result
    def read_performance_all(ckt_type, VA_path):
        params = {}
        meas_paths = []

        if ckt_type == "OP":
            file_list = FileList("test/OP")
            os.system("rm -rf test/OP/*.measure")
            os.system("rm -rf test/OP/OP.txt")
        elif ckt_type == "BGR":
            file_list = FileList("test/BGR")
            os.system("rm -rf test/BGR/*.measure")
            os.system("rm -rf test/BGR/BGR.txt")
        elif ckt_type == "LDO":
            file_list = FileList("test/LDO")
            os.system("rm -rf test/LDO/*.measure")
            os.system("rm -rf test/LDO/LDO.txt")
        elif ckt_type == "CMP":
            file_list = FileList("test/CMP")
            os.system("rm -rf test/CMP/*.measure")
            os.system("rm -rf test/CMP/CMP.txt")

        for tb_mdl in file_list.tb_mdls:
            scs_path = tb_mdl[0]
            meas_path = scs_path.replace(".scs", ".measure")
            meas_paths.append(meas_path)

            # Replace the second line in the .scs file
            with open(scs_path, "r") as file:
                lines = file.readlines()
            if len(lines) > 1:
                lines[1] = f'ahdl_include "{VA_path}"\n'
            with open(scs_path, "w") as file:
                file.writelines(lines)

            os.system(
                f"spectremdl -batch {tb_mdl[1]} -design {scs_path} -measure {meas_path} >/dev/null &"
            )
            print(
                f"running spectremdl -batch {tb_mdl[1]} -design {scs_path} -measure {meas_path} >/dev/null &"
            )

        time.sleep(0.5)

        for meas_path in meas_paths:
            count = 1
            while not os.path.exists(meas_path):
                time.sleep(1)
                count += 1
                if count > 20:
                    break

            with open(meas_path, mode="r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        params[key] = value

        directory_path = file_list.directory_path
        directory_name = os.path.basename(directory_path)
        output_file_path = os.path.join(directory_path, f"{directory_name}.txt")
        print(output_file_path)

        with open(output_file_path, "w") as output_file:
            for param, value in params.items():
                output_file.write(f"{param} = {value}\n")

        print(f"Results written to {output_file_path}")
        return output_file_path
    
    # Compare requirement and result and return ToF and str(error_dict)
    def Compare_Re(Result_path, Requirement_lines):
        def read_file_to_dict(file_path):
            """Reads a file and converts it to a dictionary based on 'key=value' format."""
            result_dict = {}
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    for line in file:
                        line = line.strip()  
                        if "=" in line:
                            key, value = line.split("=", 1)  
                            result_dict[key.strip()] = (
                                value.strip()
                            ) 
            except FileNotFoundError:
                print(f"Error: The file at {file_path} was not found.")
            except Exception as e:
                print(f"An error occurred while reading the file: {e}")
            return result_dict

        def read_lines_to_dict(lines):
            result_dict = {}
            for line in lines:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    result_dict[key.strip()] = value.strip()
            return result_dict

        result_dict = read_file_to_dict(Result_path)
        print(f"the result_dict is {result_dict}")
        requirement_dict = read_lines_to_dict(Requirement_lines)

        error_dict = {}
        
        for key, req_value in requirement_dict.items():
            if key in result_dict:
                try:
                    result_value = float(result_dict[key])
                    print(f"the result value is {result_value}")
                    req_value = float(req_value)
                    relative_error = abs(result_value - req_value) / abs(req_value)

                    # If the relative error is greater than 5% or the result is NaN, add the key to the error dictionary
                    if relative_error > 0.05 or math.isnan(result_value):
                        error_dict[key] = {
                            "result_value": result_value,
                            "requirement_value": req_value,
                            "relative_error": relative_error,
                        }
                    else:
                        print(
                            f"Key '{key}' passed. Requirement: {req_value}, Result: {result_value}"
                        )
                except ValueError:
                    print(f"Error: Non-numeric value encountered for key '{key}'.")
                    return False
            else:
                print(f"Error: Key '{key}' not found in result dictionary.")
                return False

        # If there are errors, return False and the error_dict as a string
        if error_dict:
            return False, str(error_dict)

        # If all checks pass,return True and a empty string
        return True, ""

    result_file_path = read_performance_all(ckt_type, VA_path)
    return Compare_Re(result_file_path, Requirement_lines)