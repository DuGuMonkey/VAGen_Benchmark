import os

def check_syntax(VA: str) :

    # Path where syntax check files (va,mdl, scs,log) are saved
    directory = "VAGen_check/check_syntax"

    if not os.path.exists(directory):
        os.makedirs(directory)

    va_file_path = os.path.join(directory, 'output.va')
    scs_file_path = os.path.join(directory, 'output.scs')
    log_file_path = os.path.join(directory, 'output.log')
    mdl_file_path = os.path.join(directory, 'output.mdl')

    # Save the VA string as a .va file
    try:
        with open(va_file_path, 'w') as va_file:
            va_file.write(VA)
    except Exception as e:
        print(f"Error writing to {va_file_path}: {e}")
        return False, ""
    
    # Generate a basic.mdl file. Notice: a blank line at the end
    try:
        with open(mdl_file_path, 'w') as mdl_file:
            mdl_file.write("""
        alias measurement dcmeas{
        run dc (oppoint =' logfile)
        }
        run dcmeas
                    
                            """)
    except Exception as e:
        print(f"Error writing to {mdl_file_path}: {e}")
        return False, ""
    
    Module = ""
    Ports = ""
    ToF = False
    valines = ""
    lines = ""

    # Read.va file and get Module and Ports
    try:
        with open(va_file_path, 'r') as va_file:
            for line in va_file:
                valines += line  
                if line.startswith("module"):
                    try:
                        module_start = line.index("module") + len("module")
                        module_end = line.index("(")
                        Module = line[module_start:module_end].strip()

                        ports_start = line.index("(")
                        ports_end = line.index(")") + 1
                        Ports = line[ports_start:ports_end].strip()

                        Ports = Ports.replace(",", "")

                        ToF = True
                    except ValueError as e:
                        print(f"Error parsing line: {e}")
                        return False, lines
                    break  
    except Exception as e:
        print(f"Error reading {va_file_path}: {e}")
        return False, ""

    # Generate.scs file. Notice: The first line is empty
    try:
        with open(scs_file_path, 'w') as scs_file:
            scs_file.write("\n")  
            scs_file.write(f'ahdl_include "{va_file_path}"\n')
            scs_file.write(f"I1 {Ports} {Module}\n")
    except Exception as e:
        print(f"Error writing to {scs_file_path}: {e}")
        return False, lines

    # Execute the spectremdl command
    os.system(
        f"spectremdl -batch {mdl_file_path} -design {scs_file_path} =log {log_file_path}"
    )

    # Read the log file and handle the error
    try:
        with open(log_file_path, 'r') as log_file:
            error_found = False
            error_lines = []
            for line in log_file:
                if line.startswith("Error"):
                    error_found = True
                    ToF = False
                if error_found and not line.startswith("Error") and not line.startswith("Time"):
                    error_lines.append(line)
                if line.startswith("Time") and error_found:
                    break
            if error_found:
                lines = ''.join(error_lines)
            else:
                ToF = True
                lines = ""
    except Exception as e:
        print(f"Error reading {log_file_path}: {e}")
        return False, ""

    return ToF, lines

# Example call
VA_content = """`include "discipline.h"
`include "constants.h"

`define PI  	3.14159265358979323846264338327950288419716939937511


module opamp(vout,  vin_p, vin_n, vspply_p, vspply_n);
input  vspply_p, vspply_n;
inout vout, vin_p, vin_n;
electrical vout,  vin_p, vin_n, vspply_p, vspply_n;

parameter real gain_db = 80; // DC gain in dB
parameter real freq_unitygain  = 1.0e6; // GBW,UGB
parameter real phase_margin = 60; // 
parameter real CMRR_db = 90; // In dB
parameter real PSRR_dc_db = 80; // In dB
parameter real rin = 1e6; // Input resistance
parameter real vin_offset = 0.001; // equivlant input offset voltage
parameter real ibias = 0.0; // input bias current  
parameter real iin_max = 100e-6; //  
parameter real slew_rate = 0.5e6; // slew rate
parameter real rout = 80; // equivlant output resistance
parameter real output_range_low = 0.1; // output voltage range low
parameter real output_range_high = 1.1; // output voltage range high
parameter real input_equivlant_noise_low = 1e-6; // input noise at low frequency at 1kHz -flicker noise
parameter real input_equivlant_noise_high = 1e-9; // input noise at high frequency at 1MHz -thermal noise

parameter real supply_voltage = 1.2; // supply voltage
parameter real VCM = 0.6; // common mode voltage
electrical vinp_in, vinn_in;
real c1;
real c2;
real gm_nom;
real r1;
real vmax_in;
real vin_val;
real CMRR;
real PSRR;
real gain;
electrical cout,vref_;
 
   analog begin

      @ ( initial_step or initial_step("dc") ) begin
         gain = 10**(gain_db/20); // DC gain
         CMRR = 10**(CMRR_db/20); // CMRR
         PSRR = 10**(PSRR_dc_db/20); // PSRR
         c1 = iin_max/(slew_rate); // dominant pole cap
         gm_nom = 2 * `PI * freq_unitygain * c1; // first stage transconductance
         r1 = gain/gm_nom; // dominant pole resistor
         vmax_in = iin_max/gm_nom; // input voltage range
         c2 = 1.6*tan((90-phase_margin)*`PI/180)/(2*`PI*freq_unitygain*rout); // output pole cap
      end
      
      V(vin_p,vinp_in) <+ flicker_noise((input_equivlant_noise_low*(1e3/1))**2,2,"flick") + white_noise(input_equivlant_noise_high**2,"thermal");
      V(vin_n,vinn_in) <+ 0;
      vin_val = V(vinp_in,vinn_in) + vin_offset;
	    V(vref_) <+ V(vspply_p, vspply_n)/2;
      //
      // Input stage.
      //
      I(vinp_in, vinn_in) <+ (V(vinp_in, vinn_in) + vin_offset)/ rin;
      I(vref_, vinp_in) <+ ibias;
      I(vref_, vinn_in) <+ ibias;

      //
      // GM stage with slewing
      //
      I(vref_, cout) <+ V(vref_, cout)/100e6;

      if (vin_val 
         I(vref_, cout) <+ gm_nom*vmax_in;
      else if (vin_val < -vmax_in)
         I(vref_, cout) <+ gm_nom*(-vmax_in);
      else
         I(vref_, cout) <+ gm_nom*vin_val ;

      //
      // Dominant Pole.
      //
      I(cout, vref_) <+ ddt(c1*V(cout, vref_));
      I(cout, vref_) <+ V(cout, vref_)/r1;

      //
      // Output Stage.
      //
      I(vref_, vout) <+ V(cout, vref_)/rout;
      I(vout, vref_) <+ V(vout, vref_)/rout;
      I(vout, vref_) <+ ddt(c2*V(vout, vref_));

      //
      // Soft Output Limiting.
      //
      if (V(vout) > output_range_high)
         I(cout, vref_) <+ gm_nom*(V(vout)-output_range_high);
      else if (V(vout) < output_range_low)
         I(cout, vref_) <+ gm_nom*(V(vout)-output_range_low); 

      //
      // Vout influenced by CMRR and PSRR
      //
      I(vout,vref_) <+ ((V(vinp_in)+V(vinn_in))/2-VCM)*(gain/CMRR)/rout;
	    I(vout,vref_) <+ (V(vspply_p)-supply_voltage)*(gain/PSRR)/rout;

	end
endmodule

"""
ToF, lines = check_syntax(VA_content)
print("ToF:", ToF)
print("Lines:\n", lines)
