import streamlit as st
import platform


def get_os_details():
    details = {
        "Operating System": platform.system(),
        "OS Release": platform.release(),
        "OS Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Architecture": platform.architecture(),
        "Platform": platform.platform(),
        "Node (Network name)": platform.node()
    }
    return details


def main():
    st.title("System Information App")

    st.write("This app displays information about your operating system and hardware.")

    details = get_os_details()

    for key, value in details.items():
        st.text(f"{key}: {value}")

    st.info("Note: Some information might be limited based on system permissions and configurations.")


if __name__ == "__main__":
    main()