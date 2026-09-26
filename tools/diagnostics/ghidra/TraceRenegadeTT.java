// Bounded interoperability inspection. Keep output in a private reference cache.
// Arguments: strings, "0x" addresses, "entry:0x" verified entries, "data:0x" globals.
// @category Renegade.Networking

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.Reference;
import java.util.LinkedHashSet;

public class TraceRenegadeTT extends GhidraScript {
    @Override
    public void run() throws Exception {
        LinkedHashSet<Function> functions = new LinkedHashSet<>();
        for (String selector : getScriptArgs()) {
            // Only explicit, independently verified entries may define missing
            // functions. Run the headless project with -readOnly to discard edits.
            if (selector.startsWith("entry:0x")) {
                var address = toAddr(selector.substring(8));
                Function function = getFunctionAt(address);
                if (function == null && getFunctionContaining(address) == null) {
                    disassemble(address);
                    function = createFunction(address, null);
                }
                if (function == null) throw new IllegalArgumentException("Not a function entry: " + selector);
                functions.add(function);
                continue;
            }
            // field:HEX_DISPLACEMENT:HEX_START:HEX_END limits the search to a
            // known owner range. Matches are leads, not verified field uses.
            if (selector.startsWith("field:")) {
                String[] parts = selector.split(":");
                if (parts.length != 4) throw new IllegalArgumentException(selector);
                long offset = Long.parseLong(parts[1], 16);
                long end = Long.parseLong(parts[3], 16);
                InstructionIterator instructions = currentProgram.getListing().getInstructions(toAddr(parts[2]), true);
                while (instructions.hasNext() && !monitor.isCancelled()) {
                    Instruction instruction = instructions.next();
                    if (instruction.getAddress().getOffset() >= end) break;
                    for (int operand = 0; operand < instruction.getNumOperands(); ++operand) {
                        for (Object component : instruction.getOpObjects(operand)) {
                            if (component instanceof Scalar && ((Scalar)component).getSignedValue() == offset) {
                                Function function = getFunctionContaining(instruction.getAddress());
                                if (function != null && functions.size() < 24) functions.add(function);
                                println("FIELD_CANDIDATE " + instruction.getAddress() + " " + instruction);
                            }
                        }
                    }
                }
                continue;
            }
            if (selector.startsWith("data:0x")) {
                for (Reference reference : getReferencesTo(toAddr(selector.substring(7)))) {
                    Function function = getFunctionContaining(reference.getFromAddress());
                    if (function != null && functions.size() < 24) functions.add(function);
                }
                continue;
            }
            if (selector.startsWith("0x")) {
                Function function = getFunctionContaining(toAddr(selector.substring(2)));
                if (function != null) functions.add(function);
                else println("FUNCTION_UNDEFINED " + selector);
                continue;
            }
            DataIterator data = currentProgram.getListing().getDefinedData(true);
            while (data.hasNext() && !monitor.isCancelled()) {
                Data item = data.next();
                if (!(item.getValue() instanceof String) || !selector.equals(item.getValue())) continue;
                println("STRING " + item.getAddress() + " " + selector);
                for (Reference reference : getReferencesTo(item.getAddress())) {
                    Function function = getFunctionContaining(reference.getFromAddress());
                    if (function != null) functions.add(function);
                }
            }
        }
        LinkedHashSet<Function> selected = new LinkedHashSet<>(functions);
        for (Function function : functions) {
            for (Reference reference : getReferencesTo(function.getEntryPoint())) {
                Function caller = getFunctionContaining(reference.getFromAddress());
                if (caller != null && selected.size() < 24) selected.add(caller);
            }
        }
        DecompInterface decompiler = new DecompInterface();
        try {
            if (!decompiler.openProgram(currentProgram)) throw new Exception(decompiler.getLastMessage());
            int count = 0;
            for (Function function : selected) {
                if (monitor.isCancelled() || count++ == 24) break;
                println("FUNCTION " + function.getEntryPoint() + " " + function.getName());
                DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
                if (result.decompileCompleted()) println(result.getDecompiledFunction().getC());
                else println("DECOMPILE_INCOMPLETE " + result.getErrorMessage());
            }
        } finally {
            decompiler.dispose();
        }
    }
}
