// Using Jest for JavaScript testing
describe('WiFi Template Functions', () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <div id="network-Test_Network_1" class="network">
                <div class="network-info">
                    <span class="ssid">Test Network 1</span>
                </div>
                <div id="actions-Test_Network_1" class="network-actions"></div>
            </div>
            <div id="network-Test_Network_2" class="network">
                <div class="network-info">
                    <span class="ssid">Test Network 2</span>
                </div>
                <div id="actions-Test_Network_2" class="network-actions"></div>
            </div>
        `;
    });

    test('showConnectForm should handle accordion behavior', () => {
        // First network open
        showConnectForm('Test_Network_1');
        expect(document.querySelector('#actions-Test_Network_1 .network-form')).toBeTruthy();
        
        // Open second network
        showConnectForm('Test_Network_2');
        expect(document.querySelector('#actions-Test_Network_1 .network-form')).toBeFalsy();
        expect(document.querySelector('#actions-Test_Network_2 .network-form')).toBeTruthy();
    });

    test('showConnectForm should handle null form elements', () => {
        // Test handling of non-existent elements
        showConnectForm('Non_Existent_Network');
        // Should not throw error
    });
}); 