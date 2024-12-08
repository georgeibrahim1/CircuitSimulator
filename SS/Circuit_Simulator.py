import tkinter as tk
from tkinter import messagebox, simpledialog
import math


class Node:
    def __init__(self, name):
        self.name = name
        self.elements = []


class Element:
    def __init__(self, name, voltage=0, current=0, resistance=0, node1=None, node2=None):
        self.name = name
        self.voltage = voltage
        self.current = current
        self.resistance = resistance
        self.node1 = node1
        self.node2 = node2

        self.left = None
        self.right = None
        self.children_connections = None


class CircuitCore:

    NONE = 0
    SERIES = 1
    PARALLEL = 2

    def __init__(self):
        self.elements = []
        self.nodes = []


    def add_wire(self, name, negative_side, positive_side):
        if negative_side == positive_side:
            raise ValueError("Cannot connect node to itself")
        return self.add_element(name, 0, 0, 0, negative_side, positive_side)

    def add_resistor(self, name, resistance, negative_side, positive_side):
        if negative_side == positive_side:
            raise ValueError("Cannot connect node to itself")
        return self.add_element(name, 0, 0, resistance, negative_side, positive_side)

    def add_battery(self, name, voltage, negative_side, positive_side):
        if negative_side == positive_side:
            raise ValueError("Cannot connect node to itself")
        return self.add_element(name, voltage, 0, 0, negative_side, positive_side)

    def add_element(self, name, voltage, current, resistance, negative_side, positive_side):

        if self.search_element(name):
            raise ValueError(f"Element {name} already exists")


        node1 = self.search_or_create_node(negative_side)
        node2 = self.search_or_create_node(positive_side)


        element = Element(name, voltage, current, resistance, node1, node2)


        self.elements.append(element)


        node1.elements.append(element)
        node2.elements.append(element)

        return element

    def search_element(self, name):
        return next((element for element in self.elements if element.name == name), None)

    def search_node(self, name):
        return next((node for node in self.nodes if node.name == name), None)

    def search_or_create_node(self, name):
        node = self.search_node(name)
        if not node:
            node = Node(name)
            self.nodes.append(node)
        return node

    def solve(self):


        self.validate()

        # Remove wires
        i = 0
        while i < len(self.elements):
            element = self.elements[i]
            if self.is_wire(element):
                self.remove_and_bind_element(element)
                i = 0  # Restart the process
            else:
                i += 1

        allow_merge_with_battery = False
        while len(self.elements) != 1:
            merged = False
            for i in range(len(self.elements) - 1):
                for j in range(i + 1, len(self.elements)):
                    el1, el2 = self.elements[i], self.elements[j]
                    cxn = self.connection(el1, el2)

                    if cxn == self.NONE:
                        continue
                    if not allow_merge_with_battery:
                        if self.is_battery(el1) or self.is_battery(el2):
                            continue

                    self.merge(el1, el2)
                    merged = True
                    break
                if merged:
                    break

            if not merged:
                if not allow_merge_with_battery:
                    allow_merge_with_battery = True
                else:
                    raise ValueError("Circuit cannot be reduced to a single element")

        # Calculate final current
        leftover_element = self.elements[0]
        leftover_element.current = leftover_element.voltage / leftover_element.resistance

        self.unmerge(leftover_element)


    def validate(self):
        if not self.elements:
            raise ValueError("No elements in the circuit")

        battery_count = sum(1 for element in self.elements if self.is_battery(element))
        resistor_count = sum(1 for element in self.elements if element.resistance > 0)

        if battery_count == 0:
            raise ValueError("No voltage source")
        if resistor_count == 0:
            raise ValueError("No resistor")

        for element in self.elements:
            if len(element.node1.elements) < 2 or len(element.node2.elements) < 2:
                raise ValueError("Elements are not properly connected")

    def connection(self, el1, el2):
        # If only two elements left, consider them series
        if len(self.elements) == 2:
            return self.SERIES

        common_nodes = []
        if el1.node1 == el2.node1:
            common_nodes.append(el1.node1)
        if el1.node2 == el2.node2:
            common_nodes.append(el1.node2)
        if el1.node1 == el2.node2:
            common_nodes.append(el1.node1)
        if el1.node2 == el2.node1:
            common_nodes.append(el1.node2)

        # Series
        if len(common_nodes) == 1:
            common_node = common_nodes[0]
            if len(common_node.elements) == 2:
                return self.SERIES

        # Parallel
        if len(common_nodes) == 2:
            return self.PARALLEL

        return self.NONE

    def merge(self, el1, el2):
        cxn = self.connection(el1, el2)
        if cxn == self.NONE:
            raise ValueError("Cannot merge elements")

        # Battery direction handling
        if self.is_battery(el1) and self.is_battery(el2):
            if el1.node1 == el2.node1 or el1.node2 == el2.node2:
                el2.voltage *= -1

        name = f"{el1.name}+{el2.name}"
        node1, node2 = None, None

        if cxn == self.SERIES:
            resistance = el1.resistance + el2.resistance
            voltage = el1.voltage + el2.voltage

            # Find common and opposite nodes
            common_node = None
            if el1.node1 == el2.node1:
                common_node = el1.node1
            elif el1.node2 == el2.node2:
                common_node = el1.node2
            elif el1.node1 == el2.node2:
                common_node = el1.node1
            elif el1.node2 == el2.node1:
                common_node = el1.node2

            node1 = el1.node1 if el1.node1 != common_node else el1.node2
            node2 = el2.node1 if el2.node1 != common_node else el2.node2

        elif cxn == self.PARALLEL:
            if el1.resistance < 0.000001 or el2.resistance < 0.000001:
                raise ValueError("Short circuit")

            if abs(el1.voltage) > 0.00001 or abs(el2.voltage) > 0.00001:
                raise ValueError("Cannot merge parallel elements with voltage")

            resistance = 1.0 / (1.0 / el1.resistance + 1.0 / el2.resistance)
            node1, node2 = el1.node1, el1.node2

        new_element = self.add_element(name, voltage, 0, resistance, node1.name, node2.name)
        new_element.left = el1
        new_element.right = el2
        new_element.children_connections = cxn

        self.elements.remove(el1)
        self.elements.remove(el2)

        return new_element

    def unmerge(self, element):
        if not element.left and not element.right:
            if element not in self.elements:
                self.elements.append(element)
            if element not in element.node1.elements:
                element.node1.elements.append(element)
            if element not in element.node2.elements:
                element.node2.elements.append(element)

            if not self.is_battery(element):
                element.voltage = element.current * element.resistance

            return

        left = element.left
        right = element.right
        current = element.current

        # Divide current based on connection type
        if element.children_connections == self.SERIES:
            left.current = current
            right.current = current
        elif element.children_connections == self.PARALLEL:
            # Distribute current based on resistance
            if left.resistance < 0.000001:
                left.current = current
            elif right.resistance < 0.000001:
                right.current = current
            else:
                ratio = left.resistance / right.resistance
                left.current = current / (ratio + 1)
                right.current = ratio * current / (ratio + 1)

        self.unmerge(left)
        self.unmerge(right)

        # Remove merged element
        element.node1.elements.remove(element)
        element.node2.elements.remove(element)
        self.elements.remove(element)

    def is_battery(self, element):
        return abs(element.voltage) > 0.00001

    def is_wire(self, element):
        return not self.is_battery(element) and element.resistance < 0.00001

    def remove_and_bind_element(self, element):


        # Save the first node and identify the second node
        saved_node = element.node1
        not_saved_node = element.node2

        # Check for parallel connections that would create a short circuit
        is_parallel = False

        # Check parallel connections on the first node
        for neighbor in saved_node.elements:
            if neighbor == element:
                continue
            if self.connection(element, neighbor) == self.PARALLEL:
                is_parallel = True
                break

        # If not parallel on first node, check second node
        if not is_parallel:
            for neighbor in not_saved_node.elements:
                if neighbor == element:
                    continue
                if self.connection(element, neighbor) == self.PARALLEL:
                    is_parallel = True
                    break

        # Throw error if parallel connections exist and element is a wire
        if is_parallel and self.is_wire(element):

            raise ValueError("Short circuit detected")

        # Rebind elements if no parallel connections
        if not is_parallel:
            # Create a copy of the elements list to avoid modification during iteration
            original_elements = not_saved_node.elements.copy()

            for other in original_elements:
                # Skip the element being removed
                if other == element:
                    not_saved_node.elements.remove(element)
                    continue

                # Rebind the node references
                if other.node1 == not_saved_node:
                    other.node1 = saved_node
                elif other.node2 == not_saved_node:
                    other.node2 = saved_node

                # Remove from old node and add to saved node
                not_saved_node.elements.remove(other)
                saved_node.elements.append(other)

        # Remove the now-empty node if no elements are connected
        if len(not_saved_node.elements) == 0:

            self.nodes.remove(not_saved_node)
            not_saved_node = None

        # Remove the element from its original nodes
        element.node1.elements.remove(element)
        if not_saved_node is not None:
            element.node2.elements.remove(element)

        # Remove the element from the circuit

        self.elements.remove(element)


class CircuitSimulatorGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Circuit Simulator")
        self.circuit = CircuitCore()

        # Circuit Elements Frame
        self.elements_frame = tk.LabelFrame(master, text="Circuit Elements")
        self.elements_frame.pack(padx=10, pady=10, fill="x")

        # Buttons for adding elements
        tk.Button(self.elements_frame, text="Add Battery", command=self.add_battery).pack(side="left", padx=5)
        tk.Button(self.elements_frame, text="Add Resistor", command=self.add_resistor).pack(side="left", padx=5)
        tk.Button(self.elements_frame, text="Add Wire", command=self.add_wire).pack(side="left", padx=5)

        # Circuit Analysis Frame
        self.analysis_frame = tk.LabelFrame(master, text="Circuit Analysis")
        self.analysis_frame.pack(padx=10, pady=10, fill="x")

        tk.Button(self.analysis_frame, text="Solve Circuit", command=self.solve_circuit).pack(side="left", padx=5)
        tk.Button(self.analysis_frame, text="View Elements", command=self.view_elements).pack(side="left", padx=5)

    def add_battery(self):
        name = simpledialog.askstring("Battery", "Enter battery name:")
        if not name:
            return

        voltage = simpledialog.askfloat("Battery", "Enter voltage:")
        if voltage is None:
            return

        negative = simpledialog.askstring("Battery", "Enter negative node name:")
        positive = simpledialog.askstring("Battery", "Enter positive node name:")

        try:
            self.circuit.add_battery(name, voltage, negative, positive)
            messagebox.showinfo("Success", f"Battery {name} added successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_resistor(self):
        name = simpledialog.askstring("Resistor", "Enter resistor name:")
        if not name:
            return

        resistance = simpledialog.askfloat("Resistor", "Enter resistance:")
        if resistance is None:
            return

        negative = simpledialog.askstring("Resistor", "Enter negative node name:")
        positive = simpledialog.askstring("Resistor", "Enter positive node name:")

        try:
            self.circuit.add_resistor(name, resistance, negative, positive)
            messagebox.showinfo("Success", f"Resistor {name} added successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_wire(self):
        name = simpledialog.askstring("Wire", "Enter wire name:")
        if not name:
            return

        negative = simpledialog.askstring("Wire", "Enter negative node name:")
        positive = simpledialog.askstring("Wire", "Enter positive node name:")

        try:
            self.circuit.add_wire(name, negative, positive)
            messagebox.showinfo("Success", f"Wire {name} added successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def solve_circuit(self):
        try:
            self.circuit.solve()
            messagebox.showinfo("Circuit Solved", "Circuit analysis completed successfully")
        except Exception as e:
            messagebox.showerror("Solve Error", str(e))

    def view_elements(self):
        elements_window = tk.Toplevel(self.master)
        elements_window.title("Circuit Elements")

        text_area = tk.Text(elements_window, height=20, width=50)
        text_area.pack(padx=10, pady=10)

        for element in self.circuit.elements:
            text_area.insert(tk.END, f"Name: {element.name}\n")
            text_area.insert(tk.END, f"Voltage: {element.voltage}\n")
            text_area.insert(tk.END, f"Current: {element.current}\n")
            text_area.insert(tk.END, f"Resistance: {element.resistance}\n")
            text_area.insert(tk.END, f"Nodes: {element.node1.name} - {element.node2.name}\n\n")

        text_area.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = CircuitSimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()