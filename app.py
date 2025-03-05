from flask import Flask, jsonify
import ai_agent_signal  # Import AI logic

app = Flask(__name__)

@app.route('/get_signal/<string:selected_instrument>', methods=['GET'])
def get_signal(selected_instrument):
    trade_signal = ai_agent_signal.generate_trade_signal(selected_instrument)
    return jsonify({"signal": trade_signal})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # Runs on port 5000
